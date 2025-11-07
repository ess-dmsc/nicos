import copy
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from nicos_ess.utilities.json_utils import (
    _parse_dtype,
    append_group_under,
    build_json,
    build_named_index_map,
    generate_dataset_json,
    generate_group_json,
    generate_nxlog_json,
    get_by_index_path,
    get_by_named_path,
    index_path_to_expr,
    is_dataset,
    is_group,
    make_group,
    remove_by_named_path,
    remove_dataset_under,
)


@pytest.fixture
def structure() -> Dict[str, Any]:
    """Load the test_structure.json located alongside this test file."""
    p = Path(__file__).parent / "test_structure.json"
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def structure_copy(structure: Dict[str, Any]) -> Dict[str, Any]:
    """Deep copy of the loaded structure for mutation tests."""
    return copy.deepcopy(structure)


def _children_of_named(struct: Dict[str, Any], path_map, named: str) -> List[Dict[str, Any]]:
    """Grab the 'children' list of a named group (by reference)."""
    grp = get_by_named_path(struct, path_map, named)
    assert is_group(grp)
    return grp.setdefault("children", [])  # type: ignore[return-value]


def test_parse_dtype_variants() -> None:
    assert _parse_dtype("s") == "string"
    assert _parse_dtype(1) == "int"
    assert _parse_dtype(True) == "int"
    assert _parse_dtype(3.14) == "double"
    assert _parse_dtype([5]) == "int"
    assert _parse_dtype([3.14]) == "double"
    assert _parse_dtype([]) == "string"
    class Weird: ...
    assert _parse_dtype(Weird()) == "string"


def test_generate_dataset_json_shape_and_dtype() -> None:
    node = generate_dataset_json("counts", [1, 2, 3], "cts")
    assert node["module"] == "dataset"
    assert node["config"]["name"] == "counts"
    assert node["config"]["values"] == [1, 2, 3]
    assert node["config"]["dtype"] == "int"
    assert node["attributes"] == [{"name": "units", "dtype": "string", "values": "cts"}]

    node2 = generate_dataset_json("scalar", 3.14, None)
    assert node2["config"]["dtype"] == "double"
    assert node2["attributes"][0]["values"] == ""  # None -> ""


def test_generate_group_json() -> None:
    child = generate_dataset_json("x", 1, "a.u.")
    grp = generate_group_json("sample", "NXsample", [child])
    assert grp["type"] == "group"
    assert grp["name"] == "sample"
    assert grp["attributes"][0]["values"] == "NXsample"
    assert grp["children"][0]["config"]["name"] == "x"


def test_generate_nxlog_json() -> None:
    node = generate_nxlog_json("logA", "f144", "src", "topic", "m")
    assert node["type"] == "group"
    assert node["name"] == "logA"
    assert any(a.get("values") == "NXlog" for a in node["attributes"])
    assert node["children"][0]["module"] == "f144"
    cfg = node["children"][0]["config"]
    assert cfg["source"] == "src" and cfg["topic"] == "topic"
    assert cfg["dtype"] == "double" and cfg["value_units"] == "m"


def test_build_json_from_groups() -> None:
    groups: Dict[str, Dict[str, Any]] = {
        "entry": {
            "nx_class": "NXentry",
            "children": [generate_group_json("instrument", "NXinstrument", [])],
        },
        "sample": {
            "nx_class": "NXsample",
            "children": [generate_dataset_json("T", 295.0, "K")],
        },
    }
    built = build_json(groups)
    assert len(built) == 2
    names = {g["name"] for g in built}
    assert {"entry", "sample"} <= names


def test_build_named_index_map_contains_core_groups(structure: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure, include_datasets=True)
    assert "/entry" in path_map
    assert "/entry/instrument" in path_map
    if "/entry/sample" in path_map:
        node = get_by_named_path(structure, path_map, "/entry/sample")
        assert is_group(node)


def test_get_by_named_and_index_path_agree(structure: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure, include_datasets=True)
    instr = get_by_named_path(structure, path_map, "/entry/instrument")
    idx_tokens = path_map["/entry/instrument"]
    same = get_by_index_path(structure, idx_tokens)  # type: ignore[arg-type]
    assert instr is same
    assert is_group(instr)


def test_index_path_to_expr_roundtrip_tokens() -> None:
    tokens: List[Any] = ["children", 0, "children", 3, "config"]
    expr = index_path_to_expr(tokens)
    assert expr == "['children'][0]['children'][3]['config']"


def test_mapping_includes_at_least_one_dataset(structure: Dict[str, Any]) -> None:
    """Find any dataset in the raw tree and assert mapping exposes it."""
    def walk(node: Any, names: List[str]) -> str | None:
        if isinstance(node, dict):
            if node.get("type") == "group" and isinstance(node.get("name"), str):
                names = names + [node["name"]]
            if node.get("module") == "dataset" and "config" in node:
                return "/" + "/".join(names + [node["config"]["name"]])
            for v in node.values():
                res = walk(v, names)
                if res:
                    return res
        elif isinstance(node, list):
            for item in node:
                res = walk(item, names)
                if res:
                    return res
        return None

    any_dataset_path = walk(structure, [])
    assert any_dataset_path is not None

    path_map = build_named_index_map(structure, include_datasets=True)
    assert any_dataset_path in path_map
    node = get_by_named_path(structure, path_map, any_dataset_path)
    assert is_dataset(node)


def test_build_named_index_map_on_conflict_list() -> None:
    """When duplicate names exist, 'list' should collect all index paths."""
    tree = {
        "type": "group",
        "name": "entry",
        "children": [
            {"type": "group", "name": "grp", "children": []},
            {"type": "group", "name": "grp", "children": []},
        ],
    }
    m_first = build_named_index_map(tree, include_datasets=False, on_conflict="first")
    m_list = build_named_index_map(tree, include_datasets=False, on_conflict="list")
    assert "/entry/grp" in m_first
    val = m_list["/entry/grp"]
    assert isinstance(val, list)
    assert len(val) == 2  # two separate index paths


def test_append_keeps_same_children_list_object(structure_copy: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure_copy, include_datasets=True)

    entry = get_by_named_path(structure_copy, path_map, "/entry")
    assert is_group(entry)
    children = entry.get("children")
    assert isinstance(children, list)
    children_id = id(children)
    pre_len = len(children)

    g = make_group("id_check_append", nx_class="NXlog")
    _, path_map = append_group_under(structure_copy, path_map, "/entry", g)

    assert id(entry["children"]) == children_id
    assert len(children) == pre_len + 1
    assert children[-1] is g


def test_remove_keeps_same_children_list_object(structure_copy: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure_copy, include_datasets=True)

    tmp = make_group("id_check_remove", nx_class="NXlog")
    _, path_map = append_group_under(structure_copy, path_map, "/entry", tmp)

    entry = get_by_named_path(structure_copy, path_map, "/entry")
    children = entry.get("children")
    assert isinstance(children, list)
    children_id = id(children)
    pre_len = len(children)
    assert any(c is tmp for c in children)

    removed, path_map = remove_by_named_path(
        structure_copy, path_map, "/entry/id_check_remove", which="first"
    )
    assert removed == 1

    assert id(entry["children"]) == children_id
    assert len(children) == pre_len - 1
    assert all(c is not tmp for c in children)
    assert all(c.get("name") != "id_check_remove" for c in children)


def test_remove_dataset_under_mutates_parent_children_in_place(structure_copy: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure_copy, include_datasets=True)

    ds_paths = [
        p for p in path_map
        if p.count("/") >= 2 and is_dataset(get_by_named_path(structure_copy, path_map, p))
    ]
    if not ds_paths:
        pytest.skip("No dataset found in test structure to remove.")

    ds_named = ds_paths[0]
    parent_named = "/".join(ds_named.split("/")[:-1])
    ds_name = ds_named.split("/")[-1]

    parent = get_by_named_path(structure_copy, path_map, parent_named)
    assert is_group(parent)
    children = parent.get("children")
    assert isinstance(children, list)
    children_id = id(children)

    pre_len = len(children)
    pre_count = sum(
        1 for c in children
        if isinstance(c, dict)
        and c.get("module") == "dataset"
        and c.get("config", {}).get("name") == ds_name
    )

    removed, path_map = remove_dataset_under(
        structure_copy, path_map, parent_named, ds_name, which="all"
    )

    assert id(parent["children"]) == children_id
    assert removed == pre_count
    assert len(children) == pre_len - pre_count
    assert all(
        not (c.get("module") == "dataset" and c.get("config", {}).get("name") == ds_name)
        for c in children
    )


def test_append_with_explicit_index_inserts_in_order(structure_copy: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure_copy, include_datasets=True)

    container = make_group("order_container", nx_class="NXcollection")
    _, path_map = append_group_under(structure_copy, path_map, "/entry", container)

    cont_children = _children_of_named(structure_copy, path_map, "/entry/order_container")
    assert len(cont_children) == 0

    gA = make_group("A", nx_class="NXlog")
    gB = make_group("B", nx_class="NXlog")
    gC = make_group("C", nx_class="NXlog")

    _, path_map = append_group_under(structure_copy, path_map, "/entry/order_container", gA)               # [A]
    _, path_map = append_group_under(structure_copy, path_map, "/entry/order_container", gB, insert_at=0) # [B, A]
    _, path_map = append_group_under(structure_copy, path_map, "/entry/order_container", gC, insert_at=1) # [B, C, A]

    names = [n.get("name") for n in cont_children]
    assert names == ["B", "C", "A"]


def test_refresh_map_false_updates_preheld_reference(structure_copy: Dict[str, Any]) -> None:
    path_map = build_named_index_map(structure_copy, include_datasets=True)

    entry = get_by_named_path(structure_copy, path_map, "/entry")
    children = entry.get("children")
    assert isinstance(children, list)
    pre_len = len(children)

    ghost = make_group("ghost_via_reference", nx_class="NXlog")
    _, _stale_map = append_group_under(
        structure_copy, path_map, "/entry", ghost, refresh_map=False
    )

    # Pre-held reference reflects the change even with stale map
    assert len(children) == pre_len + 1
    assert children[-1] is ghost

    with pytest.raises(KeyError):
        _ = get_by_named_path(structure_copy, path_map, "/entry/ghost_via_reference")

    path_map = build_named_index_map(structure_copy, include_datasets=True)
    node = get_by_named_path(structure_copy, path_map, "/entry/ghost_via_reference")
    assert node is ghost

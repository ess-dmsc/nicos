# json_utils.py
"""
Utilities for working with NeXus-like JSON structures.

This module provides:

1) Small JSON builders (your existing helpers, preserved as-is)
   - generate_nxlog_json
   - generate_dataset_json
   - generate_group_json
   - build_json

2) Named-path mapping (build a map from human-readable paths like
   ``/entry/instrument`` to index paths like
   ``['children', 0, 'children', 1]``)
   - build_named_index_map
   - get_by_named_path
   - index_path_to_expr
   - make_getter

3) Minimal edit helpers that rely on the mapping
   - append_group_under
   - remove_by_named_path
   - remove_dataset_under
   - make_group

----------------------------------------------------------------------
Quick start
----------------------------------------------------------------------

Build a name→index mapping and use it to get nodes:

>>> path_map = build_named_index_map(structure, include_datasets=True)
>>> instrument = get_by_named_path(structure, path_map, "/entry/instrument")
>>> expr = index_path_to_expr(path_map["/entry/instrument"])
>>> isinstance(expr, str)
True

Append/remove by named path:

>>> path_map = build_named_index_map(structure, include_datasets=True)
>>> new_instr = make_group("instrument", nx_class="NXlog")
>>> inserted_idx, path_map = append_group_under(structure, path_map, "/entry", new_instr)
>>> isinstance(inserted_idx, list)
True
>>> _, path_map = remove_dataset_under(structure, path_map, "/entry/instrument", "depends_on", which="all")
>>> _, path_map = remove_by_named_path(structure, path_map, "/entry/instrument", which="first")
"""

from __future__ import annotations

from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

Key = Union[str, int]
IndexPath = List[Key]
ConflictPolicy = Literal["first", "last", "list", "error"]
Which = Literal["first", "last", "all", "index"]


class _GroupSpec(TypedDict):
    nx_class: str
    children: List[Dict[str, Any]]


def generate_nxlog_json(
    name: str,
    schema: str,
    source: str,
    topic: str,
    units: str,
) -> Dict[str, Any]:
    """Build a minimal NXlog group node.

    Args:
        name: Group name.
        schema: Module name to use for the single child (e.g. "ev44", "dataset").
        source: Message source string.
        topic: Message topic string.
        units: Units string for the produced values (stored as ``value_units``).

    Returns:
        A dictionary representing an NXlog group with one child module.
    """
    return {
        "name": name,
        "type": "group",
        "attributes": [{"name": "NX_class", "dtype": "string", "values": "NXlog"}],
        "children": [
            {
                "module": schema,
                "config": {
                    "source": source,
                    "topic": topic,
                    "dtype": "double",
                    "value_units": units,
                },
            }
        ],
    }


def _parse_dtype(value: Any) -> str:
    """Infer a NeXus dtype string from a Python value.

    Logic is intentionally preserved:
    - ``str`` -> ``"string"``
    - ``bool`` or ``int`` -> ``"int"``
    - ``float`` -> ``"double"``
    - lists -> infer from the first element, defaulting to ``"string"`` for empty lists
    - anything else -> ``"string"``

    Args:
        value: Example value to infer the dtype from.

    Returns:
        A dtype string: ``"string"``, ``"int"``, or ``"double"``.
    """
    type_map = {str: "string", bool: "int", int: "int", float: "double"}
    if isinstance(value, list):
        return _parse_dtype(value[0]) if value else "string"
    return type_map.get(type(value), "string")


def generate_dataset_json(
    name: str,
    value: Any,
    unit: Optional[str],
) -> Dict[str, Any]:
    """Build a ``dataset`` module node with a ``units`` attribute.

    Args:
        name: Dataset name (stored in ``config.name``).
        value: Dataset values (stored in ``config.values``).
        unit: Units string for the dataset; if ``None`` or empty, an empty string is used.

    Returns:
        A dictionary representing a dataset module with dtype inferred from ``value``.
    """
    attributes = [{"name": "units", "dtype": "string", "values": unit if unit else ""}]
    return {
        "module": "dataset",
        "config": {
            "name": name,
            "values": value,
            "dtype": _parse_dtype(value),
        },
        "attributes": attributes,
    }


def generate_group_json(
    name: str,
    nx_class: str,
    children: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a group with an ``NX_class`` attribute and provided children.

    Args:
        name: Group name.
        nx_class: Value for the ``NX_class`` attribute (e.g. ``"NXinstrument"``).
        children: Child nodes to include under ``children``.

    Returns:
        A dictionary representing the group.
    """
    return {
        "name": name,
        "type": "group",
        "attributes": [{"name": "NX_class", "dtype": "string", "values": nx_class}],
        "children": children,
    }


def build_json(
    groups: Mapping[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build a list of group nodes from a mapping.

    Expects each ``groups[name]`` to contain:
      - ``"nx_class"``: ``str``
      - ``"children"``: ``List[Dict[str, Any]]``

    Args:
        groups: Mapping of group-name -> spec dict.

    Returns:
        A list of group dictionaries suitable as a JSON root.
    """
    return [
        generate_group_json(name, group["nx_class"], group["children"])
        for name, group in groups.items()
    ]


def is_group(node: Any) -> bool:
    """Return True if *node* is a group (``{'type': 'group', 'name': <str>}``)."""
    return (
        isinstance(node, dict)
        and node.get("type") == "group"
        and isinstance(node.get("name"), str)
    )


def is_dataset(node: Any) -> bool:
    """Return True if *node* is a dataset module with a ``config.name``."""
    return (
        isinstance(node, dict)
        and node.get("module") == "dataset"
        and isinstance(node.get("config"), dict)
        and isinstance(node["config"].get("name"), str)
    )


def get_dataset_name(node: Dict[str, Any]) -> str:
    """Get dataset name from a dataset node."""
    return node["config"]["name"]


def index_path_to_expr(path: Sequence[Key]) -> str:
    """Pretty-print an index path as a chained subscription expression.

    Example:
        ``['children', 0, 'children', 1]`` -> ``"['children'][0]['children'][1]"``
    """
    return "".join(f"[{repr(k)}]" for k in path)


def get_by_index_path(obj: Any, path: Sequence[Key]) -> Any:
    """Follow a list of keys/indices into a nested dict/list structure."""
    cur = obj
    for k in path:
        cur = cur[k]
    return cur


def _as_paths(entry: Union[IndexPath, List[IndexPath]]) -> List[IndexPath]:
    """Normalize a mapping value into a list of index paths."""
    if isinstance(entry, list) and entry and isinstance(entry[0], (str, int)):
        return [entry]  # a single index path
    if isinstance(entry, list):
        return entry  # already multiple paths
    return [entry]


def get_by_named_path(
    obj: Any,
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]],
    named_path: str,
) -> Any:
    """Fetch a node by its named path (e.g. ``/entry/instrument``).

    If the mapping contains multiple index paths for this named path
    (i.e., it was built with ``on_conflict='list'``), the *first* path is used.
    """
    if named_path not in mapping:
        raise KeyError(f"Named path not found: {named_path!r}")
    idx_paths = _as_paths(mapping[named_path])
    return get_by_index_path(obj, idx_paths[0])


def _store(
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]],
    key: str,
    value: IndexPath,
    on_conflict: ConflictPolicy,
) -> None:
    """Store an index path under a named key respecting the conflict policy."""
    if key not in mapping:
        mapping[key] = value
        return

    if on_conflict == "first":
        return
    if on_conflict == "last":
        mapping[key] = value
        return
    if on_conflict == "list":
        existing = mapping[key]
        if (
            isinstance(existing, list)
            and existing
            and isinstance(existing[0], (str, int))
        ):
            mapping[key] = [existing, value]  # existing was a single index path
        elif isinstance(existing, list):
            existing.append(value)  # already a list of paths
        else:
            mapping[key] = [existing, value]
        return
    if on_conflict == "error":
        raise ValueError(f"Duplicate named path encountered: {key!r}")


def build_named_index_map(
    json_obj: Any,
    *,
    include_datasets: bool = True,
    include_groups: bool = True,
    on_conflict: ConflictPolicy = "first",
) -> Dict[str, Union[IndexPath, List[IndexPath]]]:
    """Build a mapping from named paths to index paths.

    Args:
        json_obj: Root JSON object (dict/list mixed tree).
        include_datasets: Include datasets as leaf named paths
            (e.g. ``/entry/instrument/depends_on``).
        include_groups: Include groups as named paths.
        on_conflict: Behavior for duplicate named paths:
            - ``'first'`` (default): keep first occurrence;
            - ``'last'``: keep last occurrence;
            - ``'list'``: store all index paths under the same name;
            - ``'error'``: raise on duplicates.

    Returns:
        dict mapping ``"/a/b"`` to:
          - index path like ``['children', 0, ...]``, or
          - a list of such index paths (if ``on_conflict='list'``).
    """
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]] = {}

    def walk(node: Any, idx_path: IndexPath, name_stack: List[str]) -> None:
        effective_stack = name_stack
        if is_group(node):
            effective_stack = name_stack + [node["name"]]
            if include_groups:
                key = "/" + "/".join(effective_stack)
                _store(mapping, key, list(idx_path), on_conflict)

        if include_datasets and is_dataset(node):
            key = "/" + "/".join(effective_stack + [get_dataset_name(node)])  # type: ignore[list-item]
            _store(mapping, key, list(idx_path), on_conflict)

        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, idx_path + [k], effective_stack)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, idx_path + [i], effective_stack)

    walk(json_obj, [], [])
    return mapping


def make_getter(root: Any, mapping: Dict[str, Union[IndexPath, List[IndexPath]]]):
    """Return a function like ``get('/entry/instrument') -> node``."""

    def _get(named_path: str) -> Any:
        return get_by_named_path(root, mapping, named_path)

    return _get


def _resolve_named_path(
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]],
    named_path: str,
    which: Which = "first",
    index: int | None = None,
) -> List[IndexPath]:
    """Resolve a named path into one or more index paths."""
    if named_path not in mapping:
        raise KeyError(f"Named path not found: {named_path!r}")

    paths = _as_paths(mapping[named_path])
    if which == "all":
        return list(paths)
    if which == "first":
        return [paths[0]]
    if which == "last":
        return [paths[-1]]
    if which == "index":
        if index is None:
            raise ValueError("which='index' requires an explicit index")
        return [paths[index]]
    raise ValueError(f"Unknown 'which' value: {which}")


def _parent_and_key(root: Any, idx_path: Sequence[Key]) -> Tuple[Any, Key]:
    """Return ``(parent_container, last_key)`` for an index path."""
    if not idx_path:
        raise ValueError("Empty index path has no parent")
    parent = get_by_index_path(root, idx_path[:-1])
    return parent, idx_path[-1]


def _remove_at_index_path(root: Any, idx_path: Sequence[Key]) -> Any:
    """Remove and return the node at *idx_path*."""
    parent, last = _parent_and_key(root, idx_path)
    if isinstance(parent, list) and isinstance(last, int):
        return parent.pop(last)
    if isinstance(parent, dict) and isinstance(last, str):
        return parent.pop(last)
    raise TypeError(
        f"Cannot remove at {index_path_to_expr(list(idx_path))}; "
        f"parent type={type(parent).__name__}, key type={type(last).__name__}",
    )


def append_group_under(
    root: Any,
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]],
    parent_named_path: str,
    group_node: Dict[str, Any],
    *,
    insert_at: int | None = None,
    refresh_map: bool = True,
) -> Tuple[IndexPath, Dict[str, Union[IndexPath, List[IndexPath]]]]:
    """Append (or insert) a group under the parent's ``children`` list.

    Args:
        root: Root JSON object.
        mapping: Named-path mapping (from :func:`build_named_index_map`).
        parent_named_path: Named path of the parent group.
        group_node: The group node to insert.
        insert_at: Optional index to insert at (default: append).
        refresh_map: If True, rebuild the mapping after mutation.

    Returns:
        (inserted_index_path, new_mapping)
    """
    parent_idx_path = _resolve_named_path(mapping, parent_named_path, "first")[0]
    parent_group = get_by_index_path(root, parent_idx_path)

    if not isinstance(parent_group, dict):
        raise TypeError(f"Parent at {parent_named_path!r} is not a dict/group")

    children = parent_group.get("children")
    if children is None:
        parent_group["children"] = children = []
    if not isinstance(children, list):
        raise TypeError("'children' is not a list on the parent group")

    pos = len(children) if insert_at is None else int(insert_at)
    if insert_at is None:
        children.append(group_node)
    else:
        children.insert(pos, group_node)

    inserted_idx_path = list(parent_idx_path) + ["children", pos]

    if refresh_map:
        new_map = build_named_index_map(
            root, include_datasets=True, include_groups=True
        )
    else:
        new_map = mapping  # unchanged

    return inserted_idx_path, new_map


def remove_by_named_path(
    root: Any,
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]],
    named_path: str,
    *,
    which: Which = "first",
    index: int | None = None,
    refresh_map: bool = True,
) -> Tuple[int, Dict[str, Union[IndexPath, List[IndexPath]]]]:
    """Remove a dataset or group addressed by its named path.

    Args:
        root: Root JSON object.
        mapping: Named-path mapping.
        named_path: Target named path to remove.
        which: Selection mode: ``'first'``, ``'last'``, ``'all'``, or ``'index'``.
        index: Index used when ``which='index'``.
        refresh_map: If True, rebuild the mapping after mutation.

    Returns:
        (removed_count, new_mapping)
    """
    targets = _resolve_named_path(mapping, named_path, which, index)

    # Remove in stable order (for list parents: higher indices first).
    def parent_key(p: IndexPath) -> Tuple[Tuple[Key, ...], int, int]:
        parent = get_by_index_path(root, p[:-1]) if p[:-1] else root
        is_list = 1 if isinstance(parent, list) else 0
        last = p[-1]
        neg_last = -last if isinstance(last, int) else 0
        return tuple(p[:-1]), is_list, neg_last

    removed = 0
    for p in sorted(targets, key=parent_key):
        _remove_at_index_path(root, p)
        removed += 1

    if refresh_map:
        new_map = build_named_index_map(
            root, include_datasets=True, include_groups=True
        )
    else:
        new_map = mapping

    return removed, new_map


def remove_dataset_under(
    root: Any,
    mapping: Dict[str, Union[IndexPath, List[IndexPath]]],
    parent_named_path: str,
    dataset_name: str,
    *,
    which: Which = "first",
    index: int | None = None,
    refresh_map: bool = True,
) -> Tuple[int, Dict[str, Union[IndexPath, List[IndexPath]]]]:
    """Remove dataset(s) by name under a parent group.

    The target named path is constructed as ``"{parent}/{dataset_name}"``.
    """
    path = parent_named_path.rstrip("/") + "/" + dataset_name
    return remove_by_named_path(
        root,
        mapping,
        path,
        which=which,
        index=index,
        refresh_map=refresh_map,
    )


def make_group(
    name: str,
    *,
    nx_class: str | None = None,
    attributes: List[Dict[str, Any]] | None = None,
    children: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Construct a minimal group node compatible with these utilities."""
    node: Dict[str, Any] = {"type": "group", "name": name}
    if attributes or nx_class:
        node["attributes"] = list(attributes or [])
    if nx_class:
        node.setdefault("attributes", []).append(
            {"name": "NX_class", "values": nx_class, "dtype": "string"}
        )
    node["children"] = list(children or [])
    return node

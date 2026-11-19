"""Tests for the grid layout of the live view plots."""

import random

import pytest

from nicos_ess.utilities.grid_layout import (
    COLUMNS,
    add,
    arrange,
    automatic,
    bottom,
    by_row,
    from_preset,
    holes,
    insert,
    new_row,
    pack,
    resize,
    share,
    spans_of,
    swap,
)


def rects(layout):
    return {c.name: c.rect() for c in layout}


def rows(layout):
    """Return the names in each row, for layouts of plots one row high."""
    return [[c.name for c in layout if c.y == y] for y in range(bottom(layout))]


def no_overlaps(layout):
    taken = [(x, y) for c in layout for x in range(c.x, c.x + c.w) for y in c.rows()]
    return len(taken) == len(set(taken))


def seven():
    layout = pack(automatic([f"p{i}" for i in range(7)], 1920, 1000, 1.4))
    assert [c.w for c in layout] == [3, 3, 3, 3, 4, 4, 4]
    return layout


def test_plots_flow_densely_so_a_small_plot_fills_a_gap():
    layout = pack([("a", 8, 1), ("b", 6, 1), ("c", 4, 1)])
    assert rects(layout) == {"a": (0, 0, 8, 1), "c": (8, 0, 4, 1), "b": (0, 1, 12, 1)}


def test_a_gap_at_the_end_of_a_row_widens_the_plots_of_the_row():
    halves = {"a": (0, 0, 6, 1), "b": (6, 0, 6, 1)}
    assert rects(pack([("a", 4, 1), ("b", 4, 1)])) == halves
    # The narrowest plot gets the free columns first.
    assert rects(pack([("a", 3, 1), ("b", 6, 1)])) == halves


def test_a_gap_beside_a_tall_plot_is_closed_by_the_plots_around_it():
    layout = pack([("big", 6, 2), ("a", 6, 1)])
    assert rects(layout) == {"big": (0, 0, 6, 2), "a": (6, 0, 6, 2)}
    layout = pack([("big", 6, 2), ("a", 3, 1), ("b", 3, 1), ("c", 3, 1)])
    assert rects(layout)["c"] == (6, 1, 6, 1)
    assert not holes(layout)


def test_a_narrower_plot_at_the_end_of_a_row_gives_its_columns_to_the_plot_before():
    layout = resize(seven(), "p3", 2, 1)
    assert rects(layout)["p3"] == (10, 0, 2, 1)
    assert [c.w for c in layout if c.y == 0] == [3, 3, 4, 2]


def test_a_resized_plot_keeps_its_size_while_others_close_the_gap():
    spans = [("a", 4, 1), ("b", 4, 1), ("c", 4, 1), ("wide", 12, 1)]
    layout = resize(pack(spans), "wide", 8, 1)
    assert rects(layout) == {
        "a": (0, 0, 4, 1),
        "b": (4, 0, 4, 1),
        "c": (8, 0, 4, 2),
        "wide": (0, 1, 8, 1),
    }


def test_a_plot_alone_in_its_row_fills_it_whatever_the_user_does():
    alone = resize(pack([("a", 12, 1), ("b", 12, 1)]), "b", 6, 1)
    assert rects(alone)["b"] == (0, 1, 12, 1)


def test_only_the_tall_plot_beside_a_gap_gets_shorter():
    spans = [("a", 9, 3), ("b", 4, 2), ("tall", 2, 4), ("c", 8, 1), ("far", 12, 6)]
    assert rects(pack(spans)) == {
        "a": (0, 0, 9, 3),
        "tall": (9, 0, 3, 3),
        "b": (0, 3, 4, 2),
        "c": (4, 3, 8, 2),
        "far": (0, 5, 12, 6),
    }


def test_no_plot_is_higher_than_twelve_rows_even_while_resized():
    layout = pack([("a", 6, 28), ("b", 6, 1)])
    assert [c.h for c in layout] == [COLUMNS, COLUMNS]
    assert max(c.h for c in resize(layout, "b", 6, 40)) == COLUMNS


@pytest.mark.parametrize("seed", range(10))
def test_any_spans_pack_into_rows_without_holes_or_overlaps(seed):
    rng = random.Random(seed)
    for _ in range(100):
        spans = [(f"p{i}", rng.randint(0, 14), rng.randint(0, 14)) for i in range(9)]
        keep = rng.choice([None, *[s[0] for s in spans]])
        layout = pack(spans, keep)
        assert sorted(c.name for c in layout) == sorted(s[0] for s in spans)
        assert not holes(layout) and no_overlaps(layout), (spans, keep)
        assert all(1 <= c.h <= COLUMNS for c in layout)


def test_columns_are_shared_in_proportion_to_the_weights():
    assert share(12, [1, 2]) == [4, 8]
    assert share(10, [1, 3]) == [3, 7]
    assert share(5, [1, 1, 1]) == [2, 2, 2]


def test_an_automatic_row_gives_the_columns_left_over_to_its_last_plots():
    spans = automatic([f"p{i}" for i in range(5)], 5000, 500, 1.4)
    assert [w for _n, w, _h in spans] == [2, 2, 2, 3, 3]


def test_a_wider_plot_takes_the_columns_from_its_neighbours_first():
    layout = resize(seven(), "p1", 5, 1)
    assert rows(layout) == [["p0", "p1", "p2", "p3"], ["p4", "p5", "p6"]]
    assert [c.w for c in layout] == [3, 5, 2, 2, 4, 4, 4]
    narrower = resize(seven(), "p1", 2, 1)
    assert [c.w for c in narrower][:4] == [3, 2, 4, 3]


def test_a_plot_made_two_rows_high_makes_one_big_plot_with_small_ones():
    six = pack(automatic([f"p{i}" for i in range(6)], 1600, 900, 1.4))
    layout = resize(six, "p0", 6, 2)
    big = [(0, 0, 6, 2), (6, 0, 6, 1), (6, 1, 6, 1)]
    assert [c.rect() for c in layout[:3]] == big
    assert [c.rect() for c in layout[3:]] == [(0, 2, 4, 1), (4, 2, 4, 1), (8, 2, 4, 1)]


def test_plots_of_the_same_size_swap_places():
    layout = pack(swap(seven(), "p0", "p2"))
    assert rows(layout) == [["p2", "p1", "p0", "p3"], ["p4", "p5", "p6"]]
    assert rects(layout)["p0"] == rects(seven())["p2"]


def test_a_plot_dropped_into_another_row_shares_its_width():
    layout = pack(insert(seven(), "p1", "p5", False))
    assert rows(layout) == [["p0", "p2", "p3"], ["p4", "p1", "p5", "p6"]]
    assert all(c.w == 4 for c in layout if c.y == 0)
    assert all(c.w == 3 for c in layout if c.y == 1)
    after = pack(insert(seven(), "p1", "p6", True))
    assert rows(after)[1][-1] == "p1"


def test_a_row_without_room_refuses_one_more_plot():
    full = pack([(f"p{i}", 2, 1) for i in range(6)] + [("x", 12, 1)])
    assert insert(full, "x", "p0", False) is None


def test_a_plot_dropped_within_its_row_only_moves():
    layout = pack(insert(seven(), "p0", "p3", True))
    assert rows(layout)[0] == ["p1", "p2", "p3", "p0"]
    assert [c.w for c in layout] == [c.w for c in seven()]


def test_a_plot_dropped_below_the_last_row_starts_a_row():
    layout = pack(new_row(seven(), "p0"))
    assert rows(layout) == [["p1", "p2", "p3"], ["p4", "p5", "p6"], ["p0"]]
    assert rects(layout)["p0"] == (0, 2, 12, 1)
    assert [c.w for c in layout if c.y == 0] == [4, 4, 4]


def test_new_plots_join_the_last_row_while_there_is_room():
    layout = pack(add(seven(), "new"))
    assert rows(layout)[-1] == ["p4", "p5", "p6", "new"]
    crowded = pack(add(layout, "more"))
    assert rows(crowded)[-1] == ["more"]
    assert pack(add([], "first"))[0].rect() == (0, 0, COLUMNS, 1)


def test_saved_spans_leave_out_plots_that_are_gone_and_place_new_ones():
    saved = [("a", 6, 2), ("gone", 6, 1), ("b", 6, 1)]
    layout = arrange(["a", "b", "new"], saved)
    assert rects(layout) == {"a": (0, 0, 6, 2), "b": (6, 0, 6, 2), "new": (0, 2, 12, 1)}


def test_a_new_roi_plot_goes_right_after_the_plot_of_its_output():
    spans = [("monitor", 4, 1), ("ngem", 4, 1), ("other", 4, 1), ("last", 12, 1)]
    cells = arrange(["monitor", "ngem", "other", "last", "ngem.roi0"], spans)
    order = [c.name for c in by_row(cells)]
    assert order == ["monitor", "ngem", "ngem.roi0", "other", "last"]


def test_presets_give_the_order_and_spans_of_the_plots():
    patterns = {"m_*": (6, 0, 6, 1), "a": (0, 0, 6, 2)}
    spans = from_preset(["m_1", "a", "image"], patterns)
    assert spans == [("a", 6, 2), ("m_1", 6, 1)]


def test_a_preset_for_the_own_name_wins_over_a_wildcard():
    patterns = {"m_*": (6, 0, 6, 1), "m_2": (0, 0, 6, 2)}
    spans = from_preset(["m_1", "m_2"], patterns)
    assert spans == [("m_2", 6, 2), ("m_1", 6, 1)]


@pytest.mark.parametrize("count", range(1, 13))
@pytest.mark.parametrize("width, height", [(1920, 1000), (1000, 1000), (800, 1600)])
def test_automatic_layouts_fill_whole_rows(count, width, height):
    layout = pack(automatic([f"p{i}" for i in range(count)], width, height, 1.4))
    shown = rects(layout)
    assert len(layout) == count, shown
    assert no_overlaps(layout), shown
    assert not holes(layout), shown
    assert all(c.h == 1 for c in layout), shown
    assert all(c.w >= 2 for c in layout), shown
    counts = [len(r) for r in rows(layout)]
    assert max(counts) - min(counts) <= 1, shown
    assert counts == sorted(counts, reverse=True), shown
    assert min(counts) > 1 or max(counts) == 1, shown


@pytest.mark.parametrize(
    "count, width, height, counts",
    [
        (1, 1920, 1000, [1]),
        (2, 1920, 1000, [2]),
        (4, 1920, 1000, [2, 2]),
        (7, 1920, 1000, [4, 3]),
        (12, 1920, 1000, [4, 4, 4]),
        (3, 800, 1600, [1, 1, 1]),
    ],
)
def test_automatic_layouts_follow_the_shape_of_the_panel(count, width, height, counts):
    layout = pack(automatic([f"p{i}" for i in range(count)], width, height, 1.4))
    assert [len(r) for r in rows(layout)] == counts


@pytest.mark.parametrize("seed", range(20))
def test_no_sequence_of_changes_loses_a_plot_or_leaves_a_hole(seed):
    rng = random.Random(seed)
    layout = pack(
        automatic([f"p{i}" for i in range(rng.randint(1, 12))], 1600, 900, 1.4)
    )
    for step in range(60):
        names = [c.name for c in layout]
        name = rng.choice(names)
        others = [n for n in names if n != name]
        kind = rng.choice(["swap", "insert", "resize", "row", "add", "remove"])
        if not others and kind in ("swap", "insert", "remove"):
            continue
        expected = set(names)
        if kind == "swap":
            spans = swap(layout, name, rng.choice(others))
        elif kind == "insert":
            target = rng.choice(others)
            spans = insert(layout, name, target, rng.random() < 0.5)
            spans = spans or spans_of(layout)
        elif kind == "resize":
            w, h = rng.randint(1, COLUMNS), rng.randint(1, 3)
            spans = spans_of(resize(layout, name, w, h))
        elif kind == "row":
            spans = new_row(layout, name)
        elif kind == "add":
            spans = add(layout, f"n{step}")
            expected.add(f"n{step}")
        else:
            spans = [s for s in spans_of(layout) if s[0] != name]
            expected.discard(name)
        layout = pack(spans)
        assert sorted(c.name for c in layout) == sorted(expected), (kind, name)
        assert not holes(layout), (kind, name, rects(layout))
        assert no_overlaps(layout)
        assert all(c.x >= 0 and c.x + c.w <= COLUMNS for c in layout)
        # What the user sees is what is saved.
        assert rects(pack(spans_of(layout))) == rects(layout)

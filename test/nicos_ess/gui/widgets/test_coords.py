import math

import pytest

from nicos_ess.gui.widgets.pyqtgraph.coords import CoordinateGrid


def test_pixels_map_to_bin_centres_and_back():
    grid = CoordinateGrid([0.0, 2.0, 4.0, 6.0], [-1.0, 0, 1])
    assert grid.pixel_to_world(1, 0) == (3.0, -0.5)
    assert grid.world_to_pixel(3.0, -0.5) == (1.0, 0.0)


@pytest.mark.parametrize(
    "edges, pixel_and_world",
    [
        (
            [0.0, 1.0, 2.0, 4.0, 8.0, 16.0],
            [(-0.4, 0.1), (0.0, 0.5), (1.3, 1.8), (3.0, 6.0), (4.0, 12.0), (5.0, 20.0)],
        ),
        (
            [8.0, 6.0, 4.0, 2.0, 0.0],
            [(-0.4, 7.8), (0.0, 7.0), (1.3, 4.4), (3.0, 1.0), (4.0, -1.0)],
        ),
    ],
)
def test_uneven_and_falling_axes_map_both_ways(edges, pixel_and_world):
    grid = CoordinateGrid(edges, [-0.5, 0.5])
    for pixel, world in pixel_and_world:
        assert grid.pixel_to_world(pixel, 0)[0] == pytest.approx(world)
        assert grid.world_to_pixel(world, 0.0)[0] == pytest.approx(pixel)


@pytest.mark.parametrize(
    "edges, world, pixel",
    [([0.0, 0.0, 1.0, 2.0], 0.0, -0.5), ([0.0, 1.0, 1.0], 2.0, 1.5)],
)
def test_a_zero_width_bin_gives_a_finite_pixel(edges, world, pixel):
    grid = CoordinateGrid(edges, [-0.5, 0.5])
    result = grid.world_to_pixel(world, 0.0)[0]
    assert math.isfinite(result)
    assert result == pixel


def test_grids_on_equal_edges_are_the_same():
    grid = CoordinateGrid([0.0, 1.0, 2.0], [0.0, 1.0])
    assert grid.same_as(CoordinateGrid([0.0, 1.0, 2.0], [0.0, 1.0]))
    assert not grid.same_as(None)
    assert not grid.same_as(CoordinateGrid([0.0, 1.0, 3.0], [0.0, 1.0]))
    assert not grid.same_as(CoordinateGrid([0.0, 1.0, 2.0], [0.0, 2.0]))

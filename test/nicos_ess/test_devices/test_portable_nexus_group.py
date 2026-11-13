import numpy as np

from nicos_ess.devices.datasinks.portable_nexus_group import ngem_pixel_offsets


def test_ngem_geometry_has_one_pixel_per_id():
    detector_number, x, y, z = ngem_pixel_offsets()
    assert detector_number.shape == (2, 128, 128)
    assert x.shape == y.shape == z.shape == detector_number.shape
    assert np.array_equal(np.sort(detector_number.ravel()), np.arange(1, 32769))


def test_ngem_geometry_planes_and_extent():
    detector_number, x, y, z = ngem_pixel_offsets()
    # front plane (ids 1..16384) at +5 mm, back plane at -5 mm along the beam
    assert detector_number[0].min() == 1 and detector_number[0].max() == 16384
    assert np.all(z[0] == 0.005) and np.all(z[1] == -0.005)
    # 0.3 x 0.3 m, pixel centres
    assert np.isclose(x.min(), -0.1488) and np.isclose(x.max(), 0.1488)
    assert np.isclose(y.max(), 0.1488) and np.isclose(y.min(), -0.1488)
    # id 1 is the top left pixel, ids run along x first
    assert (x[0, 0, 0], y[0, 0, 0]) == (x.min(), y.max())
    assert detector_number[0, 0, 1] == 2 and detector_number[0, 1, 0] == 129

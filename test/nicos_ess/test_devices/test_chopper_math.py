"""The chopper widget's geometry against what was seen on real discs.

Every disc here is described as in the NeXus file and the chopper records
(slit_edges, beam_position, resolver_sign, tdc_resolver_position). The expected
positions come from outside this model: the HEIMDAL lab drawing (May 2026), the
ODIN Airbus FAT report (RWN-RP-ADSF-ODIN-1001811670, Table 6-1, resolver reading
with each cut-out at the neutron window) and the DREAM measured open park.
"""

import pytest

from nicos_ess.devices.chopper_math import (
    check_geometry,
    clockwise,
    parked_rotation_deg,
    spinning_rotation_deg,
    wrap360,
)

DOWN = 270.0
UP = 90.0
LEFT = 180.0


def centre(chopper, rotation, index=0):
    start, end = chopper["slit_edges"][index]
    return wrap360(rotation + (start + end) / 2.0)


def disc(edges, beam_position, resolver_sign, tdc, **extra):
    return dict(
        chopper="disc",
        slit_edges=edges,
        beam_position=beam_position,
        resolver_sign=resolver_sign,
        tdc_resolver_position=tdc,
        legacy_spd_sign=True,
        **extra,
    )


# HEIMDAL TPSC-101 (motor upstream) and TPSC-102 (motor downstream).
TPSC101 = disc([[0.0, 5.2]], 354.3, -1, 341.3)
TPSC102 = disc([[0.0, 5.2]], 15.2, 1, 341.9)

# ODIN WFMC1 (Airbus, motor upstream) and its FAT Table 6-1 park readings.
WFMC1 = disc(
    [
        [0.0, 5.7],
        [48.65, 57.65],
        [94.32, 106.32],
        [137.1, 152.0],
        [177.27, 194.77],
        [214.91, 234.91],
    ],
    8.47,
    1,
    0.0,
)
WFMC1_FAT_PARK = [-5.62, 44.68, 91.85, 136.08, 177.55, -143.56]

# DREAM PSC2, beam drawn above the axle; opening 6 is parked open at 49.3.
PSC2 = disc(
    [
        [0.0, 2.46],
        [28.23, 31.83],
        [57.03, 60.63],
        [143.615, 146.845],
        [157.995, 161.265],
        [215.345, 219.115],
        [258.46, 262.4],
        [316.72, 319.34],
    ],
    193.13,
    1,
    342.0,
    guide_position="UP",
)


@pytest.mark.parametrize(
    ("chopper", "reading", "where"),
    [
        (TPSC101, 333.0, DOWN),
        (TPSC101, 243.0, LEFT),
        (TPSC102, 329.3, DOWN),
        (TPSC102, 59.3, LEFT),
    ],
)
def test_heimdal_parked_as_seen_in_the_lab(chopper, reading, where):
    rotation = parked_rotation_deg(chopper, reading)
    assert centre(chopper, rotation) == pytest.approx(where)


@pytest.mark.parametrize(
    ("chopper", "speed", "observed_phase", "lag"),
    [
        (TPSC101, 70.0, 357.0, 5.3),
        (TPSC101, -70.0, 14.9, 6.6),
        (TPSC102, 70.0, 18.85, 6.25),
        (TPSC102, -70.0, 352.9, 5.5),
    ],
)
def test_heimdal_spinning_as_seen_in_the_lab(chopper, speed, observed_phase, lag):
    """The lab phase includes the drive's lag, which neither NeXus nor the
    widget model; without it the window is centred on the beam."""
    rotation = spinning_rotation_deg(chopper, observed_phase - lag, speed)
    assert centre(chopper, rotation) == pytest.approx(DOWN)


@pytest.mark.parametrize("index", range(6))
def test_odin_wfmc1_every_cut_out_parked_at_its_fat_reading(index):
    rotation = parked_rotation_deg(WFMC1, WFMC1_FAT_PARK[index])
    assert centre(WFMC1, rotation, index) == pytest.approx(DOWN)


def test_dream_psc2_parked_open_with_the_beam_above():
    rotation = parked_rotation_deg(PSC2, 49.3)
    assert centre(PSC2, rotation, 6) == pytest.approx(UP)


@pytest.mark.parametrize(
    ("chopper", "index", "where", "mechdly_cw", "mechdly_ccw"),
    [
        (WFMC1, 0, DOWN, 5.62, 354.38),
        (PSC2, 6, UP, 292.7, 67.3),
    ],
)
def test_expected_mechdly_centres_the_opening(
    chopper, index, where, mechdly_cw, mechdly_ccw
):
    """MechDly from the chopper records (computed there, not here)."""
    for speed, phase in ((14.0, mechdly_cw), (-14.0, mechdly_ccw)):
        rotation = spinning_rotation_deg(chopper, phase, speed)
        assert centre(chopper, rotation, index) == pytest.approx(where)


def test_spdnex_sign_is_the_default():
    spdnex = dict(TPSC101, legacy_spd_sign=False)
    assert clockwise(TPSC101, 14.0)
    assert not clockwise(spdnex, 14.0)
    assert spinning_rotation_deg(spdnex, 351.7, -70.0) == pytest.approx(
        spinning_rotation_deg(TPSC101, 351.7, 70.0)
    )


# DREAM OC-103 (Juelich): no resolver; the pickup fires with the cut-out centred
# on the beam and the drive parks open on stop (Juelich SAT sec. 14).
OVERLAP = disc([[0.0, 27.6]], 13.8, None, None)


@pytest.mark.parametrize("reading", [None, 0.0, 123.4])
def test_dream_overlap_parks_open_whatever_pos_r_says(reading):
    check_geometry(OVERLAP)
    assert centre(OVERLAP, parked_rotation_deg(OVERLAP, reading)) == pytest.approx(DOWN)


def test_dream_overlap_spinning_is_centred_at_zero_delay():
    rotation = spinning_rotation_deg(OVERLAP, 0.0, 14.0)
    assert centre(OVERLAP, rotation) == pytest.approx(DOWN)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"slit_edges": []}, "slit_edges"),
        ({"slit_edges": [[0.0, 1.0, 2.0]]}, "slit_edges"),
        ({"beam_position": None}, "beam_position"),
        ({"guide_position": "SIDEWAYS"}, "guide_position"),
    ],
)
def test_check_geometry_names_what_is_missing(change, message):
    with pytest.raises(ValueError, match=message):
        check_geometry(dict(TPSC101, **change))

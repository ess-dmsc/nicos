# ruff: noqa: E402

import numpy as np
import pytest

pytest.importorskip(
    "nicos.guisupport.qt", reason="PyQt is required for ChopperPanel imports"
)

from nicos_ess.devices.epics.chopper import (
    CHOPPER_GUI_CHOPPER,
    CHOPPER_GUI_DELAY_ERRORS_KEY,
    CHOPPER_GUI_PARK_ANGLE_KEY,
    CHOPPER_GUI_SPEED_KEY,
    CHOPPER_GUI_TOTAL_DELAY_KEY,
    CHOPPER_GUI_VISUAL_GEOMETRY_VERIFIED,
)
from nicos_ess.gui.panels.chopper import (
    CHOPPER_KEY_ROLE_PARK_ANGLE,
    CHOPPER_KEY_ROLE_SPEED,
    CHOPPER_KEY_ROLE_TOTAL_DELAY,
    ChopperPanel,
)


def _panel_without_qt_init():
    panel = ChopperPanel.__new__(ChopperPanel)
    panel._unverified_geometry_warning = _RecordingWarningLabel()
    return panel


class _RecordingWarningLabel:
    def __init__(self):
        self._text = ""
        self._visible = False

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setVisible(self, visible):
        self._visible = visible

    def isVisible(self):
        return self._visible


class _RecordingWidget:
    def __init__(self):
        self.speeds = {}
        self.park_angles = {}
        self.angles = {}
        self.cleared = []
        self.chopper_data = []
        self.selected = None

    def set_chopper_speed(self, chopper_name, speed):
        self.speeds[chopper_name] = speed

    def set_chopper_park_angle(self, chopper_name, angle):
        self.park_angles[chopper_name] = angle

    def set_chopper_angle(self, chopper_name, angle):
        self.angles[chopper_name] = angle

    def clear_chopper_angle(self, chopper_name):
        self.cleared.append(chopper_name)
        self.angles.pop(chopper_name, None)

    def update_chopper_data(self, chopper_data):
        self.chopper_data = chopper_data

    def get_selected_chopper(self):
        return self.selected


class _RecordingLog:
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append(message % args)


class _FakeClient:
    def __init__(self, chopper_infos):
        self.chopper_infos = chopper_infos

    def eval(self, expression, default=None):
        if expression == "session.devices":
            return dict.fromkeys(self.chopper_infos)
        if expression.startswith("hasattr("):
            return True
        for name, info in self.chopper_infos.items():
            if repr(name) in expression:
                return info
        return default


def _canonical(name, **overrides):
    data = {
        CHOPPER_GUI_CHOPPER: name,
        CHOPPER_GUI_SPEED_KEY: f"{name}_speed/value",
        CHOPPER_GUI_TOTAL_DELAY_KEY: f"{name}_delay/value",
        CHOPPER_GUI_PARK_ANGLE_KEY: f"{name}_park/value",
        CHOPPER_GUI_DELAY_ERRORS_KEY: f"{name}_errors/raw_errors",
        "slit_edges": [[0.0, 90.0]],
        "motor_position": "downstream",
        "positive_speed_rotation_direction": "CW",
        "resolver_positive_direction": "CW",
        "parked_opening_index": 0,
        "tdc_resolver_position": 60.0,
        "park_open_angle": 30.0,
        "guide_position": "DOWN",
        "disk_delay": 0.0,
        CHOPPER_GUI_VISUAL_GEOMETRY_VERIFIED: False,
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "samples",
    [
        [],
        [0.0],
        [5.0, 5.0, 5.0],
        [0.0, 10.0],
        [0.0, 100.0, 200.0, 300.0],
    ],
)
def test_delay_error_stats_handles_empty_constant_narrow_and_normal_inputs(samples):
    panel = _panel_without_qt_init()

    x, y, mean, stddev, fwhm, left_edge, right_edge = panel._calc_stats(samples)

    if not samples:
        assert x.size == 0
        assert y.size == 0
        assert np.isnan(mean)
        assert np.isnan(stddev)
        assert fwhm == 0.0
        assert np.isnan(left_edge)
        assert np.isnan(right_edge)
        return

    assert y.sum() == len(samples)
    assert np.isfinite(mean)
    assert np.isfinite(stddev)
    assert np.isfinite(fwhm)
    assert left_edge < right_edge


def test_delay_error_stats_uses_defined_single_sample_stddev():
    panel = _panel_without_qt_init()

    _, _, mean, stddev, fwhm, left_edge, right_edge = panel._calc_stats([5.0])

    assert mean == pytest.approx(5.0)
    assert stddev == pytest.approx(0.0)
    assert fwhm == pytest.approx(100.0)
    assert left_edge == pytest.approx(-45.0)
    assert right_edge == pytest.approx(55.0)


def test_mode_switching_clears_stale_angle_until_active_input_arrives():
    panel = _panel_without_qt_init()
    panel.chopper_widget = _RecordingWidget()
    panel._speeds = {}
    panel._total_delays = {}
    panel._park_angles = {}

    panel._handle_park_angle_update("c1", 123.0)
    assert panel.chopper_widget.angles == {}

    panel._handle_speed_update("c1", 0.0)
    assert panel.chopper_widget.angles["c1"] == pytest.approx(123.0)

    panel._handle_speed_update("c1", 14.0)
    assert "c1" not in panel.chopper_widget.angles
    assert panel.chopper_widget.cleared[-1] == "c1"

    panel._handle_total_delay_update("c1", 10_000_000.0)
    assert panel.chopper_widget.angles["c1"] == pytest.approx(50.4)

    panel._handle_speed_update("c1", 0.0)
    assert panel.chopper_widget.angles["c1"] == pytest.approx(123.0)


@pytest.mark.parametrize(
    ("role", "cache_name"),
    [
        (CHOPPER_KEY_ROLE_SPEED, "_speeds"),
        (CHOPPER_KEY_ROLE_TOTAL_DELAY, "_total_delays"),
        (CHOPPER_KEY_ROLE_PARK_ANGLE, "_park_angles"),
    ],
)
def test_expired_motion_inputs_clear_the_active_draw_angle(role, cache_name):
    panel = _panel_without_qt_init()
    panel.chopper_widget = _RecordingWidget()
    panel.histogram_widget = None
    panel.trend_widget = None
    panel._speeds = {"c1": 14.0}
    panel._total_delays = {"c1": 1.0}
    panel._park_angles = {"c1": 2.0}
    panel._chopper_key_roles = {"some/key": ("c1", role)}

    panel.on_keyChange("some/key", 1.0, 0.0, expired=True)

    assert "c1" not in getattr(panel, cache_name)
    if role in (CHOPPER_KEY_ROLE_SPEED, CHOPPER_KEY_ROLE_TOTAL_DELAY):
        assert panel.chopper_widget.cleared[-1] == "c1"


def test_invalid_canonical_metadata_is_logged_and_not_loaded():
    valid = _canonical("valid")
    invalid = _canonical("invalid", parked_opening_index=3)
    panel = _panel_without_qt_init()
    panel.client = _FakeClient({"valid": valid, "invalid": invalid})
    panel.chopper_widget = _RecordingWidget()
    panel.log = _RecordingLog()

    panel._get_chopper_info()

    assert panel.chopper_widget.chopper_data == [valid]
    assert panel.log.warnings == [
        "Ignoring chopper invalid with invalid GUI metadata: "
        "parked_opening_index must reference an existing slit opening "
        "(got 3, total openings=1)"
    ]


def test_unverified_geometry_warning_tracks_loaded_choppers():
    verified = _canonical("verified", visual_geometry_verified=True)
    unverified_1 = _canonical("unverified_1")
    unverified_2 = _canonical("unverified_2")
    panel = _panel_without_qt_init()
    panel.client = _FakeClient(
        {
            "verified": verified,
            "unverified_1": unverified_1,
            "unverified_2": unverified_2,
        }
    )
    panel.chopper_widget = _RecordingWidget()
    panel.log = _RecordingLog()

    panel._get_chopper_info()

    assert panel._unverified_geometry_warning.isVisible()
    assert panel._unverified_geometry_warning.text() == (
        "UNVERIFIED CHOPPER GEOMETRY: openings and angles for "
        "unverified_1, unverified_2 have not been verified. Do not use this "
        "visualization as truth."
    )

    verified_2 = _canonical("verified_2", visual_geometry_verified=True)
    panel.client = _FakeClient({"verified": verified, "verified_2": verified_2})

    panel._get_chopper_info()

    assert not panel._unverified_geometry_warning.isVisible()
    assert panel._unverified_geometry_warning.text() == ""

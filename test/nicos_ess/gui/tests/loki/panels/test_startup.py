"""Startup coverage for LoKI panels."""

from __future__ import annotations

from test.nicos_ess.gui.doubles.fake_transport import DeviceSpec
from test.nicos_ess.gui.helpers import assert_panel_starts_clean


def seed_spectrometer_devices(fake_daemon):
    for name in ("hr4", "qepro"):
        fake_daemon.add_device(
            DeviceSpec(
                name=name,
                valuetype=float,
                params={
                    "_wavelengths": [400.0, 500.0, 600.0],
                    "_spectrum_array": [1.0, 2.0, 3.0],
                    "_light_array": [1.0, 1.0, 1.0],
                    "_dark_array": [0.1, 0.1, 0.1],
                    "acquireunits": "ms",
                    "status": (0, "Idle"),
                    "darkvalid": True,
                    "lightvalid": True,
                    "integrationtime": 10.0,
                    "boxcarwidth": 1,
                    "acquiremode": "single",
                },
            ),
            setup="spectrometers",
        )


def test_spectrometer_panel_starts_without_warnings_or_errors(
    gui_window_from_name, fake_daemon, caplog, qtbot
):
    assert_panel_starts_clean(
        gui_window_from_name=gui_window_from_name,
        fake_daemon=fake_daemon,
        caplog=caplog,
        qtbot=qtbot,
        guiconfig_name="loki/panels/spectrometer.py",
        panel_class="nicos_ess.loki.gui.panels.spectrometer.SpectrometerPanel",
        seed_daemon=seed_spectrometer_devices,
    )

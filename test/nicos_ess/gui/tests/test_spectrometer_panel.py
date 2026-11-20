"""The LoKI spectrometer panel on the fake daemon."""

from __future__ import annotations

import math

import pytest

from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANEL = "nicos_ess.loki.gui.panels.spectrometer.SpectrometerPanel"
guiconfig_string = single_panel_guiconfig_string(PANEL)


@pytest.fixture
def panel(gui_window_factory, fake_daemon, qtbot):
    for name, integration_time in (("hr4", 10.0), ("qepro", 20.0)):
        fake_daemon.add_device(
            DeviceSpec(
                name=name,
                valuetype=float,
                params={
                    "_wavelengths": [400.0, 500.0, 600.0],
                    "_spectrum_array": [1.0, 2.0, 0.05],
                    "_light_array": [1.0, 1.0, 1.0],
                    "_dark_array": [0.1, 0.1, 0.1],
                    "acquireunits": "ms",
                    "status": (0, "Idle"),
                    "darkvalid": True,
                    "lightvalid": True,
                    "integrationtime": integration_time,
                    "boxcarwidth": 1,
                    "acquiremode": "single",
                },
            ),
            setup="spectrometers",
        )
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, PANEL)
    qtbot.waitUntil(
        lambda: panel.spectrometer_controller.detector_combo.count() == 2,
        timeout=2000,
    )
    return panel


def test_selecting_a_spectrometer_polls_it_and_shows_its_readbacks(panel, fake_daemon):
    controller = panel.spectrometer_controller

    controller.detector_combo.setCurrentText("qepro")

    sent = fake_daemon.sent_scripts("eval")
    assert "qepro.asyncPollVolatileParams()" in sent
    assert "qepro.pollParams()" not in sent
    assert controller.integration_time.readback.text() == "20.0"


def test_absorbance_is_the_log_of_light_over_spectrum(panel):
    controller = panel.spectrometer_controller

    controller.calculate_absorbance.click()

    plotted = panel.plotwidget_1d.data[-1]["curve"][1]
    assert plotted[0] == pytest.approx(0.0)
    assert plotted[1] == pytest.approx(math.log10(0.9 / 1.9))
    # (1 - 0.1) / (0.05 - 0.1) is negative and has no logarithm: kept as is
    assert plotted[2] == pytest.approx(-18.0)

"""The ODIN and TBL live data panels with their camera control, on the fake daemon."""

from __future__ import annotations

import pytest

from nicos.core import ArrayDesc
from test.nicos_ess.gui.doubles import DeviceSpec
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)

PANELS = [
    pytest.param("nicos_ess.odin.gui.panels.live.MultiLiveDataPanel", id="odin"),
    pytest.param("nicos_ess.tbl.gui.panels.live.MultiLiveDataPanel", id="tbl"),
]


@pytest.fixture(params=PANELS)
def panel(request, gui_window_factory, fake_daemon, qtbot):
    fake_daemon.add_device(
        DeviceSpec(
            name="orca",
            valuetype=float,
            params={
                "status": (200, "Idle"),
                "acquiretime": 0.25,
                "acquireperiod": 0.5,
                "startx": 0,
                "starty": 0,
                "sizex": 2048,
                "sizey": 1024,
                "numimages": 3,
                "imagemode": "single",
                "binning": "1x1",
            },
        ),
        setup="cameras",
        loaded=True,
    )
    fake_daemon.set_cache("exp/detlist", ["area_detector_collector"])
    fake_daemon.evals["area_detector_collector.arrayInfo()"] = [
        ArrayDesc("orca", (1024, 2048), "<u2")
    ]
    window = gui_window_factory(
        guiconfig_string=single_panel_guiconfig_string(request.param)
    )
    panel = get_panel_by_class(window, request.param)
    qtbot.waitUntil(
        lambda: panel.ad_controller.detector_combo.currentText() == "orca",
        timeout=2000,
    )
    return panel


def test_selected_camera_is_polled_and_its_readbacks_shown(panel, fake_daemon):
    control = panel.ad_controller
    sent = fake_daemon.sent_scripts("eval")

    assert "orca.asyncPollVolatileParams()" in sent
    assert "orca.pollParams()" not in sent
    assert control.acquisition_time.readback.text() == "0.25"
    assert control.size_x.readback.text() == "2048"
    assert control.num_images.readback.text() == "3"
    assert control.acquisition_time.isEnabled()

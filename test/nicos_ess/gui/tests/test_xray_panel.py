"""Tests of the YMIR X-ray panel for camera start and stop and image corrections."""

import numpy as np
import pytest

from nicos.core import LIVE
from nicos.core.status import BUSY
from nicos.guisupport.qt import QMessageBox, QPushButton
from nicos.protocols.daemon import STATUS_RUNNING
from nicos.utils import byteBuffer
from nicos_ess.gui.panels.xray import XrayPanel
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas
from nicos_ess.utilities.live_frame import Frame, encode
from test.nicos_ess.gui.helpers import get_panel_by_class, single_panel_guiconfig_string

QUEUED_TIP = "Count queued. Stop takes it out of the queue."


@pytest.fixture
def xray(gui_window_factory, fake_daemon):
    config = single_panel_guiconfig_string(
        XrayPanel, camera="cam", collector="cam_collector"
    )
    panel = get_panel_by_class(gui_window_factory(guiconfig_string=config), XrayPanel)
    fake_daemon.command_log.clear()
    return panel


def command_names(fake_daemon):
    return [command for command, _ in fake_daemon.command_log]


@pytest.fixture
def queue_ids(fake_daemon, monkeypatch):
    """Record the request ids that the fake daemon hands out for queued scripts."""
    handle, ids = fake_daemon.handle, []

    def recording(command, args):
        ok, reply = handle(command, args)
        if command == "queue":
            ids.append(reply)
        return ok, reply

    monkeypatch.setattr(fake_daemon, "handle", recording)
    return ids


def send_image(xray, value, exposure):
    image = Frame(
        np.full((4, 5), float(value)),
        ("y", "x"),
        name="cam_collector",
        meta={"exposure": exposure},
    )
    datadescs, data, labels = encode([image])
    params = dict(uid=0, time=0, det="cam", tag=LIVE, datadescs=datadescs)
    blobs = [bytes(byteBuffer(b)) for b in [*data, *labels]]
    xray.client.livedata.emit(params, blobs)


def take_button(xray, which):
    (button,) = [
        b
        for b in xray.findChildren(QPushButton)
        if b.text() == "Take" and b.toolTip().endswith(f"as the {which}")
    ]
    return button


def test_the_canvas_uses_the_white_plot_style(xray):
    canvas = xray.findChild(FrameCanvas)
    assert canvas.backgroundBrush().color().name() == "#ffffff"


def test_start_queues_one_count_through_the_collector(xray, fake_daemon):
    xray.image_mode_menu.setCurrentText("multiple")
    xray.bwnum_images.setValue(4)
    xray.bstart.click()
    assert fake_daemon.sent_scripts() == ["count(cam_collector, cam=4)"]
    assert not xray.bstart.isEnabled()
    assert xray.bstart.toolTip() == QUEUED_TIP

    xray.bstart.click()
    assert fake_daemon.sent_scripts() == ["count(cam_collector, cam=4)"]
    # The image mode goes into the count preset and is not set on the camera.
    assert fake_daemon.sent_scripts("exec") == []


def test_stop_takes_a_queued_count_out_of_the_queue(
    xray, fake_daemon, queue_ids, qtbot
):
    xray.bstart.click()
    (reqid,) = queue_ids

    xray.bstop.click()
    assert fake_daemon.command_log[-1] == ("unqueue", (reqid,))
    assert fake_daemon.sent_scripts("exec") == []
    assert "finish" not in command_names(fake_daemon)

    fake_daemon.push("blocked", [reqid])
    qtbot.waitUntil(xray.bstart.isEnabled)
    assert xray.bstart.toolTip() == (
        "The request was taken out of the queue and did not run."
    )


def test_stop_finishes_a_running_count_and_keeps_its_images(
    xray, fake_daemon, queue_ids, qtbot
):
    xray.bstart.click()
    (reqid,) = queue_ids
    fake_daemon.push("processing", {"reqid": reqid})
    qtbot.waitUntil(lambda: xray.bstart.toolTip() == "Counting (started here)")

    xray.bstop.click()
    assert command_names(fake_daemon)[-1] == "finish"
    assert "unqueue" not in command_names(fake_daemon)
    assert fake_daemon.sent_scripts("exec") == []


def test_continuous_mode_runs_live_and_stop_stops_the_collector(
    xray, fake_daemon, queue_ids, qtbot
):
    xray.image_mode_menu.setCurrentText("continuous")
    xray.bstart.click()
    assert fake_daemon.sent_scripts() == ["live(cam_collector)"]
    (reqid,) = queue_ids
    fake_daemon.push("processing", {"reqid": reqid})
    fake_daemon.push("done", {"reqid": reqid, "success": True})
    qtbot.waitUntil(xray.bstart.isEnabled)

    # live() has returned, but the collector still acquires.
    xray.bstop.click()
    assert fake_daemon.sent_scripts("exec") == ["stop(cam_collector)"]
    assert "unqueue" not in command_names(fake_daemon)
    assert "finish" not in command_names(fake_daemon)


def test_a_camera_started_elsewhere_is_only_stopped_after_a_yes(
    xray, fake_daemon, monkeypatch, qtbot
):
    fake_daemon.push_cache("cam/status", (BUSY, "acquiring"))
    qtbot.waitUntil(lambda: xray.camera_status == (BUSY, "acquiring"))
    answers = []

    def question(*_args):
        return answers.pop(0)

    monkeypatch.setattr(QMessageBox, "question", question)
    answers.append(QMessageBox.StandardButton.No)
    xray.bstop.click()
    assert answers == []
    assert fake_daemon.sent_scripts("exec") == []

    answers.append(QMessageBox.StandardButton.Yes)
    xray.bstop.click()
    assert answers == []
    assert fake_daemon.sent_scripts("exec") == ["stop(cam_collector)"]


def test_start_says_how_many_scripts_run_first(
    xray, fake_daemon, queue_ids, monkeypatch, qtbot
):
    handle = fake_daemon.handle

    def busy(command, args):
        ok, reply = handle(command, args)
        # Script 5 runs while script 7 and the count of the panel wait.
        if command == "getstatus":
            reply.update(
                status=(STATUS_RUNNING, 1),
                requests=[{"reqid": 7}, {"reqid": queue_ids[-1]}],
            )
        return ok, reply

    monkeypatch.setattr(fake_daemon, "handle", busy)
    xray.bstart.click()
    assert xray.bstart.toolTip() == (
        "Count queued, and 2 scripts run first. Stop takes it out of the queue."
    )

    fake_daemon.push("done", {"reqid": 5, "success": True})
    qtbot.waitUntil(
        lambda: (
            xray.bstart.toolTip()
            == "Count queued, and 1 script runs first. Stop takes it out of the queue."
        )
    )
    fake_daemon.push("processing", {"reqid": 7})
    fake_daemon.push("done", {"reqid": 7, "success": True})
    qtbot.waitUntil(lambda: xray.bstart.toolTip() == QUEUED_TIP)
    fake_daemon.push("processing", {"reqid": queue_ids[-1]})
    qtbot.waitUntil(lambda: xray.bstart.toolTip() == "Counting (started here)")


def test_take_keeps_the_background_with_its_exposure(xray, qtbot):
    send_image(xray, 10, exposure=0.25)
    assert not xray.correction_boxes["background"].isEnabled()
    take_button(xray, "background").click()
    assert xray.reference_labels["background"].text() == "at 0.25 s"
    assert xray.correction_boxes["background"].isEnabled()

    xray.correction_boxes["background"].setChecked(True)
    assert xray.view.view.data.tolist() == np.zeros((4, 5)).tolist()

    send_image(xray, 10, exposure=1.0)
    note = "background taken at 0.25 s, exposure now 1 s"
    qtbot.waitUntil(lambda: xray.view.correction_note == note, timeout=2000)


def test_the_flat_field_divides_the_image_without_its_background(xray):
    send_image(xray, 10, exposure=0.25)
    take_button(xray, "background").click()
    xray.correction_boxes["background"].setChecked(True)

    send_image(xray, 30, exposure=0.25)
    assert not xray.correction_boxes["flat field"].isEnabled()
    take_button(xray, "flat field").click()
    assert xray.reference_labels["flat field"].text() == "at 0.25 s"
    xray.correction_boxes["flat field"].setChecked(True)

    send_image(xray, 50, exposure=0.25)
    # The image is (50 - 10) / (30 - 10).
    assert xray.view.view.data.tolist() == np.full((4, 5), 2.0).tolist()
    assert xray.view.correction_note == ""

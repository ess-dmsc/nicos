"""NICOS X-ray panel."""

from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.core.status import BUSY
from nicos.guisupport.qt import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QLabel,
    QLocale,
    QMessageBox,
    QObject,
    QPushButton,
    QSpinBox,
    QTimer,
    QWidget,
    pyqtSignal,
)
from nicos.protocols.cache import cache_load
from nicos.protocols.daemon import STATUS_IDLE, STATUS_IDLEEXC
from nicos.utils import findResource
from nicos_ess.gui.live_hub import hub_for
from nicos_ess.gui.widgets.pyqtgraph import theme
from nicos_ess.gui.widgets.pyqtgraph.corrections import SHOWN
from nicos_ess.gui.widgets.pyqtgraph.frame_plot import FrameCanvas, FrameView

FILTERS = (
    "No filter",
    "Al 1.2mm",
    "Fe 0.3mm",
    "Cu 0.35mm",
    "Cu0.35mm Fe0.3mm",
    "Cu 0.65mm",
)
# Each edit has the field, the device option, the parameter and the command that
# the panel sends when the value differs.
EDITS = (
    ("bwvoltage", "voltage", "value", "move(voltage, {})"),
    ("bwcurrent", "current", "value", "move(current, {})"),
    ("bwfocus", "focus", "value", "move(focus, {})"),
    ("bwalign_x", "align_x", "value", "move(align_x, {})"),
    ("bwalign_y", "align_y", "value", "move(align_y, {})"),
    ("bwacquire_time", "camera", "acquiretime", "set({dev}, 'acquiretime', {})"),
    ("bwacquire_period", "camera", "acquireperiod", "set({dev}, 'acquireperiod', {})"),
    ("bwnum_images", "camera", "numimages", "set({dev}, 'numimages', {})"),
    ("bwsource_motor", "source_motor", "value", "move({dev}, {})"),
    ("bwflatpanel_motor", "flatpanel_motor", "value", "move({dev}, {})"),
)
LIGHT = "background-color: {}; border-radius: 20px; border: 3px solid black;"
# Each status value has a status text, a warmup text and a light colour. The light
# blinks when the colour is None.
STATUS = {
    "NOT READY": ("ERROR", "Not warmed up", "red"),
    "WARMUP YET": ("READY FOR WARMUP", "Not warmed up", "gray"),
    "WARMUP": ("WARMUP", "Warming up", None),
    "STANDBY": ("READY FOR X-RAYS", "Warmup complete", "orange"),
    "XON": ("X-Ray ON", "Warmup complete", "limegreen"),
    "OVER": ("OVERLOAD", "Overload", "red"),
}


def _format_number(value):
    return "" if value is None else f"{value:g}"


class Acquisition(QObject):
    """A camera acquisition that the panel starts via the script queue.

    Stop only affects what the panel started. It takes a queued request out of
    the queue, finishes a running count early and keeps its images, and stops
    live(). Another acquisition on the camera, for example from a scan, is only
    stopped after the user confirms, and then only the detector is stopped.
    """

    changed = pyqtSignal()

    def __init__(self, client, parent):
        super().__init__(parent)
        self.client = client
        self.reqid = self.kind = self.detector = None
        self.running = False  # True while the request of the panel runs.
        self.live = None  # The detector that still acquires after live() returned.
        # The requests that run before the request of the panel. None stands
        # for the script that runs now.
        self.ahead = set()
        self.note = ""
        client.processing.connect(self._on_processing)
        client.blocked.connect(self._on_blocked)
        client.done.connect(self._on_done)
        client.disconnected.connect(lambda: self._finished(""))

    @property
    def pending(self):
        return self.reqid is not None

    def start(self, detector, camera, mode, images):
        if self.pending:
            return
        self.kind = "live" if mode == "Continuous" else "count"
        command = (
            f"live({detector})"
            if self.kind == "live"
            else (f"count({detector}, {camera}={images})")
        )
        self.reqid, self.detector = self.client.run(command), detector
        state = self.client.ask("getstatus", quiet=True, default={})
        queued = [r.get("reqid") for r in state.get("requests", ())]
        self.ahead = set()
        if self.reqid in queued:
            self.ahead = set(queued[: queued.index(self.reqid)])
            if state["status"][0] not in (STATUS_IDLE, STATUS_IDLEEXC):
                self.ahead.add(None)
        self.running, self.live, self.note = False, None, ""
        self.changed.emit()

    def stop(self, detector, busy, confirm):
        if self.pending and not self.running:
            self.client.tell("unqueue", self.reqid)
        elif self.pending and self.kind == "count":
            self.client.tell_action("finish")
        elif self.pending or self.live == detector:
            self.client.tell("exec", f"stop({detector})")
            self.live = None
        elif busy and confirm(
            f"The camera was not started from this panel, so it may be part of"
            f" someone's script. Stop {detector} anyway? The script itself"
            f" keeps running."
        ):
            self.client.tell("exec", f"stop({detector})")
        else:
            return
        self.changed.emit()

    def _on_processing(self, request):
        reqid = request.get("reqid")
        self.running = reqid is not None and reqid == self.reqid
        self.changed.emit()

    def _on_blocked(self, reqids):
        self.ahead -= set(reqids)
        if self.reqid in reqids:
            self._finished("The request was taken out of the queue and did not run.")
        else:
            self.changed.emit()

    def _on_done(self, request):
        self.ahead -= {request.get("reqid"), None}
        if self.reqid is None or request.get("reqid") != self.reqid:
            self.changed.emit()
        elif request.get("success", True):
            self.live = self.detector if self.kind == "live" else None
            self._finished("")
        else:
            self._finished(f"The {self.kind} ended with an error or was stopped.")

    def _finished(self, note):
        self.reqid, self.running, self.note = None, False, note
        self.changed.emit()

    def describe(self):
        """Return the request's state for the tool tip of Start."""
        if not self.pending:
            return self.note
        if self.running:
            return (
                "Counting (started here)" if self.kind == "count" else "Starting live"
            )
        text = f"{self.kind.capitalize()} queued"
        if self.ahead:
            n = len(self.ahead)
            text += f", and {n} script{' runs' if n == 1 else 's run'} first"
        return text + ". Stop takes it out of the queue."


class XrayPanel(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/ymir/gui/xray.ui"))
        self.opt = options.get  # The options name the devices.

        # The view shows the camera image with its corrections. The image comes
        # from the shared live data under the name of the camera.
        self.view = FrameView(self.opt("camera") or "camera")
        self.place_panel.addWidget(FrameCanvas(self.view), 1)
        self.place_panel.addWidget(self._corrections_bar())
        # The plot menu can change the corrections too.
        self.view.changed.connect(self._show_corrections)
        self.hub = hub_for(client, self.log)
        self.hub.arrived.connect(self.on_live_data)
        self.camera_status = None
        self.status_value = None
        self.acquisition = Acquisition(client, self)
        self.acquisition.changed.connect(self._show_acquisition)

        # The boxes take a decimal point in every locale and exposures below 1 ms.
        for box in (self.bwacquire_time, self.bwacquire_period):
            box.setLocale(QLocale.c())
            box.setDecimals(4)
            box.setMinimum(0)
        self.bwnum_images.setMinimum(1)
        self.image_mode_menu.addItems(["single", "multiple", "continuous"])
        self.filter_menu.addItems(FILTERS)
        self.filter_menu.currentTextChanged.connect(
            lambda text: self.exec_command(f"move(filter_menu, '{text}')")
        )
        for box in self.findChildren(QSpinBox):  # Scrolling must not change values.
            box.wheelEvent = lambda *event: None

        for name, device, pname, command in EDITS:
            field = getattr(self, name)
            field.editingFinished.connect(
                lambda f=field, d=device, p=pname, c=command: self._edited(f, d, p, c)
            )
        for device in ("warmup", "reset", "align_beam", "align_all", "align_stop"):
            getattr(self, f"b{device}").pressed.connect(
                lambda d=device: self.exec_command(f"move({d}, '')")
            )
        self.bxray.pressed.connect(self.toggle_xray)
        self.bstart.pressed.connect(self.start)
        self.bstop.pressed.connect(self.stop)

        self.timer = QTimer(self)  # The timer blinks the warmup light.
        self.timer.timeout.connect(self.blink)
        self.blink_on = False
        client.setup.connect(self.on_client_setup)
        client.cache.connect(self.on_client_cache)

    def _corrections_bar(self):
        """Return the controls for the background and the flat field."""
        bar = QWidget()
        grid = QGridLayout(bar)
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setVerticalSpacing(2)
        self.correction_boxes, self.reference_labels = {}, {}
        for row, (which, attr, text) in enumerate(
            (("background", "subtract", "Subtract"), ("flat field", "divide", "Divide"))
        ):
            grid.addWidget(QLabel(which.capitalize()), row, 0)
            take = QPushButton("Take")
            take.setToolTip(f"Keep the image shown now as the {which}")
            take.clicked.connect(lambda _c=False, w=which: self.view.take_reference(w))
            grid.addWidget(take, row, 1)
            box = self.correction_boxes[which] = QCheckBox(text)
            box.toggled.connect(lambda on, a=attr: self.view.set_correction(a, on))
            grid.addWidget(box, row, 2)
            label = self.reference_labels[which] = QLabel("none")
            label.setStyleSheet(f"color: {theme.MUTED};")
            grid.addWidget(label, row, 3)
        grid.addWidget(QLabel("Show"), 2, 0)
        self.shown_menu = QComboBox()
        self.shown_menu.addItems(SHOWN)
        self.shown_menu.activated.connect(
            lambda _i: self.view.set_correction("shown", self.shown_menu.currentText())
        )
        grid.addWidget(self.shown_menu, 2, 1, 1, 2)
        forget = QPushButton("Forget both")
        forget.clicked.connect(lambda: self.view.set_correction(None, None))
        grid.addWidget(forget, 2, 3)
        grid.setColumnStretch(3, 1)
        self._show_corrections()
        return bar

    def _show_corrections(self):
        corrections = self.view.corrections
        for which, box in self.correction_boxes.items():
            taken = corrections.references[which] is not None
            exposure = corrections.exposures[which]
            text = f"at {exposure:g} s" if exposure is not None else "taken"
            self.reference_labels[which].setText(text if taken else "none")
            box.blockSignals(True)
            box.setEnabled(taken)
            box.setChecked(
                corrections.subtract if which == "background" else corrections.divide
            )
            box.blockSignals(False)
        self.shown_menu.setCurrentText(corrections.shown)

    def on_live_data(self, names):
        if self.opt("camera") in names:
            self.view.show_frame(*self.hub.outputs[self.opt("camera")])

    def on_client_setup(self):
        if self.client.getDeviceList():
            self.load_data()

    def on_client_cache(self, data):
        _time, key, _op, value = data
        if "/" not in key:
            return
        devname, pname = key.split("/")
        camera = devname == str(self.opt("camera")).lower()
        if camera and pname == "status":
            try:
                self.camera_status = cache_load(value) if value else None
            except ValueError:
                self.camera_status = None
            self._show_acquisition()
        elif pname != "value":
            return
        elif devname == str(self.opt("source_motor")).lower():
            self.brsource_motor.setText(str(round(float(value), 2)))
        elif devname == str(self.opt("flatpanel_motor")).lower():
            self.brflatpanel_motor.setText(str(round(float(value), 2)))
        elif devname == str(self.opt("status")).lower():
            self.status_value = self.client.getDeviceParam(self.opt("status"), "value")
            self.status()

    def exec_command(self, command):
        self._exec_reqid = self.client.run(command)

    def param(self, device, name="value"):
        return self.client.getDeviceParam(device, name)

    def load_data(self):
        for name, device, pname, _command in EDITS:
            if "align" not in name:
                value = self.param(self.opt(device), pname)
                getattr(self, name).setValue(value)
                if device == "camera":
                    getattr(self, name.replace("bw", "br", 1)).setText(
                        _format_number(value)
                    )
        self.brbeam_align.setText(self.param(self.opt("beam_align")))
        for label, device in (
            (self.brvacuum, self.opt("vacuum")),
            (self.brtemperature, self.opt("temperature")),
            (self.brvoltage, self.opt("voltage_r")),
            (self.brcurrent, self.opt("current_r")),
        ):
            label.setText(str(self.param(device)))
        self._show_xray(self.param(self.opt("xray")))
        self._show_power(self.bwvoltage.value(), self.bwcurrent.value())
        cam = self.opt("camera")
        self.image_mode_menu.setCurrentText(str(self.param(cam, "imagemode")).lower())
        self.camera_status = self.param(cam, "status")
        self._show_acquisition()
        self.status_value = self.param(self.opt("status"))
        self.status()
        # The panel starts without a filter and counts with the collector of the camera.
        self.exec_command("move(filter_menu, 'No filter')")
        self.exec_command(f"SetDetectors({self.opt('collector')})")

    def status(self):
        if self.status_value not in STATUS:
            self.timer.stop()
            return
        text, info, color = STATUS[self.status_value]
        self.brstatus.setText(text)
        self.warmup_info.setText(info)
        if color is None:
            self.timer.start(500)
        else:
            self.timer.stop()
            self.status_light.setStyleSheet(LIGHT.format(color))

    def blink(self):
        self.blink_on = not self.blink_on
        self.status_light.setStyleSheet(
            LIGHT.format("orange" if self.blink_on else "gray")
        )

    def _show_xray(self, value):
        if value in ("XON", "XOF"):
            on = value == "XON"
            self.xray_info.setText("X-ray ON" if on else "X-ray OFF")
            self.bxray.setText("Turn OFF" if on else "Turn ON")

    def toggle_xray(self):
        value = self.param(self.opt("xray"))
        if value in ("XON", "XOF"):
            new = "XOF" if value == "XON" else "XON"
            self.exec_command(f"move(xray, '{new}')")
            self._show_xray(new)

    def _show_power(self, voltage, current):
        # The read-backs can lag right after a change, so this uses the set values.
        self.progress_voltage.setValue(int(round(voltage - 20) / 280 * 100))
        self.progress_current.setValue(int(round(current / 10)))
        power = voltage * current * 1e-3
        self.brpower.setText(str(round(power)))
        self.progress_power.setValue(int(round(power / 230 * 100)))

    def _edited(self, field, device, pname, command):
        device = self.opt(device)
        value = field.value()
        if self.param(device, pname) == value:
            return
        self.exec_command(command.format(repr(value), dev=device))
        if field is self.bwvoltage:
            self._show_power(value, self.param(self.opt("current")))
        elif field is self.bwcurrent:
            self._show_power(self.param(self.opt("voltage")), value)
        elif device == self.opt("camera"):
            getattr(self, field.objectName().replace("bw", "br", 1)).setText(
                f"{value:g}"
            )

    def start(self):
        # Count with the collector so that the images reach the live views. The
        # image mode sets the preset of the count, and "multiple" uses the
        # number of images.
        mode = self.image_mode_menu.currentText()
        images = 1 if mode == "single" else self.bwnum_images.value()
        self.acquisition.start(
            self.opt("collector"), self.opt("camera"), mode.capitalize(), images
        )

    def stop(self):
        status = self.camera_status
        busy = isinstance(status, (tuple, list)) and status[0] == BUSY
        self.acquisition.stop(self.opt("collector"), busy, self.confirm)

    def confirm(self, question):
        answer = QMessageBox.question(self, "Stop the camera?", question)
        return answer == QMessageBox.StandardButton.Yes

    def _show_acquisition(self):
        pending = self.acquisition.pending
        self.bstart.setEnabled(not pending)
        self.bstart.setText("Queued…" if pending else "Start")
        self.bstart.setToolTip(self.acquisition.describe())

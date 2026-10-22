from nicos.guisupport.qt import (
    QComboBox,
    QDialog,
    QDoubleValidator,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    pyqtSignal,
    sip,
)
from nicos.protocols.cache import cache_load
from nicos.utils import number_types
from nicos_ess.devices.chopper_math import phase_deg
from nicos_ess.gui.panels.parameters_table import ParametersTable
from nicos_ess.gui.panels.utils import (
    attach_status_resources,
    setBackgroundBrush,
    setForegroundBrush,
)

MOTION_KEYS = ("speed_readback", "speed_setpoint", "delay")
INPUT_WIDTH = 150
BUTTON_WIDTH = 120

# parameter -> (label in the Disc box, or None if shown elsewhere; unit)
READBACKS = {
    "in_phase": ("In phase", ""),
    "total_delay": ("Total delay", "ns"),
    "delay_mean": ("Delay error mean", "ns"),
    "delay_stddev": ("Delay error std dev", "ns"),
    "delay_fwhm": ("Delay error FWHM", "ns"),
    "park_status": (None, ""),
    "park_position": (None, "deg"),
    "command": (None, ""),
}


class ChopperDialog(QDialog):
    """Dialog to control an ESS chopper disc: speed and phase first, then
    parking, the drive commands and the IOC's delay statistics."""

    closed = pyqtSignal(object)

    def __init__(self, parent, devname, devinfo, devitem, log, expert):
        QDialog.__init__(self, parent)
        attach_status_resources(self)
        self.log = log
        self.devices_panel = parent
        self.client = parent.client
        self.devname = devname
        self.devinfo = devinfo
        self.devitem = devitem
        self.param_table = ParametersTable(
            parent, self.client, self.devname, self.devices_panel
        )
        self.setWindowTitle(f"Control {devname}")

        self._build_ui()
        self._reinit()

        if expert:
            self.dialog_layout.insertWidget(
                self.dialog_layout.count() - 1, self.param_table
            )
        else:
            self.dialog_layout.insertItem(
                self.dialog_layout.count() - 1,
                QSpacerItem(
                    0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
                ),
            )
        self.resize(self.sizeHint())

    def _build_ui(self):
        self.dialog_layout = QVBoxLayout(self)

        self.description = QLabel()
        self.state = QLabel()
        font = self.state.font()
        font.setBold(True)
        self.state.setFont(font)
        self.status_icon = QLabel()
        self.status_text = QLabel()
        self.status_text.setWordWrap(True)
        self.status_text.setAutoFillBackground(True)
        self.status_text.setMargin(4)
        state_row = QHBoxLayout()
        state_row.addWidget(self.status_icon)
        state_row.addWidget(self.state)
        state_row.addStretch()
        self.dialog_layout.addWidget(self.description)
        self.dialog_layout.addLayout(state_row)
        self.dialog_layout.addWidget(self.status_text)

        motion, grid = self._group("Speed and phase")
        self.speed = QLabel()
        self.speed_target = self._number_edit("target (Hz)")
        self.btn_speed = self._button("Move")
        self.phase = QLabel()
        self.phase_target = self._number_edit("target (deg)")
        self.btn_phase = self._button("Move")
        self.btn_stop = self._button("Stop disc")
        self._row(grid, 0, "Speed", self.speed, self.speed_target, self.btn_speed)
        self._row(grid, 1, "Phase", self.phase, self.phase_target, self.btn_phase)
        grid.addWidget(self.btn_stop, 2, 3)

        self.readbacks = {param: QLabel() for param in READBACKS}
        info, grid = self._group("Disc")
        for column, params in enumerate(
            (("in_phase", "total_delay"), ("delay_mean", "delay_stddev", "delay_fwhm"))
        ):
            for row, param in enumerate(params):
                grid.addWidget(QLabel(f"{READBACKS[param][0]}:"), row, 2 * column)
                grid.addWidget(self.readbacks[param], row, 2 * column + 1)

        parking, grid = self._group("Parking (stopped disc)")
        self.park_choice = self._choice("The IOC's park commands")
        self.btn_park = self._button("Park")
        self.park_angle = self._number_edit("angle (deg)")
        self.btn_park_angle = self._button("Park")
        self._row(
            grid,
            0,
            "Position",
            self.readbacks["park_status"],
            self.park_choice,
            self.btn_park,
        )
        self._row(
            grid,
            1,
            "Angle",
            self.readbacks["park_position"],
            self.park_angle,
            self.btn_park_angle,
        )

        drive, grid = self._group("Drive")
        self.command_choice = self._choice("The IOC's drive commands")
        self.btn_command = self._button("Send")
        self.btn_reset = self._button("Clear alarms")
        self._row(
            grid,
            0,
            "Command",
            self.readbacks["command"],
            self.command_choice,
            self.btn_command,
        )
        grid.addWidget(self.btn_reset, 1, 3)

        buttons = QHBoxLayout()
        self.btn_history = QPushButton("History")
        self.btn_close = QPushButton("Close")
        buttons.addWidget(self.btn_history)
        buttons.addStretch()
        buttons.addWidget(self.btn_close)
        self.dialog_layout.addLayout(buttons)

        self.btn_speed.clicked.connect(self._move_speed)
        self.speed_target.returnPressed.connect(self._move_speed)
        self.btn_stop.clicked.connect(self._stop_disc)
        self.btn_phase.clicked.connect(self._move_phase)
        self.phase_target.returnPressed.connect(self._move_phase)
        self.btn_park.clicked.connect(self._park)
        self.btn_park_angle.clicked.connect(self._park_at_angle)
        self.btn_command.clicked.connect(self._send_command)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_history.clicked.connect(
            lambda: self.devices_panel.plot_history(self.devname)
        )
        self.btn_close.clicked.connect(self.close)

    def _group(self, title):
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setColumnMinimumWidth(0, 100)
        grid.setHorizontalSpacing(12)
        grid.setColumnMinimumWidth(1, 120)
        grid.setColumnStretch(4, 1)
        self.dialog_layout.addWidget(box)
        return box, grid

    @staticmethod
    def _row(grid, row, name, value, target, button):
        grid.addWidget(QLabel(f"{name}:"), row, 0)
        grid.addWidget(value, row, 1)
        grid.addWidget(target, row, 2)
        grid.addWidget(button, row, 3)

    @staticmethod
    def _button(text):
        button = QPushButton(text)
        button.setFixedWidth(BUTTON_WIDTH)
        return button

    @staticmethod
    def _choice(tooltip):
        combo = QComboBox()
        combo.setMinimumWidth(INPUT_WIDTH)
        combo.setPlaceholderText("choose")
        combo.setToolTip(tooltip)
        return combo

    @staticmethod
    def _number_edit(placeholder):
        edit = QLineEdit()
        edit.setValidator(QDoubleValidator())
        edit.setPlaceholderText(placeholder)
        edit.setFixedWidth(INPUT_WIDTH)
        return edit

    def _reinit(self):
        if sip.isdeleted(self.devitem):
            self.devitem = self.devices_panel._devitems.get(self.devname.lower())
            if self.devitem is None:
                self.close()
                return

        self.params = self.client.getDeviceParams(self.devname)
        self.param_table.set_params(
            self.params, self.client.getDeviceParamInfo(self.devname)
        )
        self.devrepr = (
            repr(self.devname)
            if "namespace" not in self.params.get("visibility", ("namespace",))
            else self.devname
        )

        self.description.setText(self.params.get("description", ""))
        self.description.setVisible(bool(self.params.get("description")))
        self._fill_choices(self.park_choice, "park")
        self._fill_choices(self.command_choice, "command")
        self.state.setText(self.devinfo.fmtValUnit().strip())
        self._update_status(*self.devinfo.status)
        for param in READBACKS:
            self._update_param(param, self.params.get(param))
        self._motion = {key: self.params.get(key) for key in MOTION_KEYS}
        self._update_motion()

    def _fill_choices(self, combo, param):
        choices = self.client.eval(
            f"session.getDevice({self.devname!r}).parameters[{param!r}].type.vals",
            (),
        )
        combo.clear()
        combo.addItems([str(choice) for choice in choices or ()])
        combo.setCurrentIndex(-1)

    def _update_motion(self, key=None, value=None):
        """Speed and phase from the disc's speed and delay cache keys."""
        if key is not None:
            self._motion[key] = value
        speed = self._motion.get("speed_readback")
        self.speed.setText("" if speed is None else f"{speed:.3f} Hz")
        delay = self._motion.get("delay")
        setpoint = self._motion.get("speed_setpoint")
        if delay is None or setpoint is None:
            self.phase.setText("")
        else:
            self.phase.setText(f"{phase_deg(delay, setpoint):.3f} deg")

    def _update_status(self, status, message):
        self.status_text.setText(message)
        self.status_icon.setPixmap(self.statusIcon[status].pixmap(16, 16))
        setForegroundBrush(self.status_text, self.fgBrush[status])
        setBackgroundBrush(self.status_text, self.bgBrush[status])

    def _update_param(self, param, value):
        if param in READBACKS:
            unit = READBACKS[param][1]
            if isinstance(value, number_types):
                value = f"{value:,.1f}".replace(",", "\u2009")
            self.readbacks[param].setText(
                "" if value is None else f"{value} {unit}".strip()
            )

    def _exec(self, command):
        self.devices_panel.exec_command(command)

    def _target(self, edit):
        try:
            return float(edit.text())
        except ValueError:
            return None

    def _move_speed(self):
        target = self._target(self.speed_target)
        if target is not None:
            self._exec(f"move({self.devrepr}.speed, {target!r})")

    def _stop_disc(self):
        self._exec(f"move({self.devrepr}.speed, 0)")

    def _move_phase(self):
        target = self._target(self.phase_target)
        if target is not None:
            self._exec(f"move({self.devrepr}.phase, {target!r})")

    def _park(self):
        if self.park_choice.currentIndex() >= 0:
            choice = self.park_choice.currentText()
            self._exec(f"set({self.devname!r}, 'park', {choice!r})")

    def _park_at_angle(self):
        angle = self._target(self.park_angle)
        if angle is not None:
            self._exec(f"set({self.devname!r}, 'park_angle', {angle!r})")

    def _send_command(self):
        if self.command_choice.currentIndex() >= 0:
            choice = self.command_choice.currentText()
            self._exec(f"set({self.devname!r}, 'command', {choice!r})")

    def _reset(self):
        self._exec(f"reset({self.devrepr})")

    def closeEvent(self, event):
        event.accept()
        self.closed.emit(self.devname.lower())

    def on_cache_params(self, subkey, value):
        if subkey in MOTION_KEYS:
            self._update_motion(subkey, cache_load(value) if value else None)
        elif value:
            self._update_param(subkey, cache_load(value))
            if subkey in self.params:
                self.param_table.update_param(subkey, str(cache_load(value)))

    def on_cache(self, time, subkey, op, value):
        if subkey == "value":
            self.state.setText(self.devinfo.fmtValUnit().strip())
        elif subkey == "status":
            self._update_status(*self.devinfo.status)

from types import SimpleNamespace

import pytest

from nicos_ess.gui.panels import devices


EPICS_MOTOR_LIMIT_CASES = [
    pytest.param(
        -10.0,
        (-100.0, 150.0),
        (-90.0, 110.0),
        (-110.0, 140.0),
        id="positive-direction-negative-offset",
    ),
    pytest.param(
        25.0,
        (-100.0, 150.0),
        (-55.0, 145.0),
        (-75.0, 175.0),
        id="positive-direction-positive-offset",
    ),
    pytest.param(
        -10.0,
        (-100.0, 150.0),
        (-130.0, 70.0),
        (-160.0, 90.0),
        id="negative-direction-negative-offset",
    ),
    pytest.param(
        25.0,
        (-100.0, 150.0),
        (-95.0, 105.0),
        (-125.0, 125.0),
        id="negative-direction-positive-offset",
    ),
]

MOVEABLE_LIMIT_CASES = [
    pytest.param(
        None,
        (-100.0, 150.0),
        (-100.0, 150.0),
        (-100.0, 150.0),
        id="normal-moveable-without-offset",
    ),
    pytest.param(
        10.0,
        (-100.0, 150.0),
        (-90.0, 120.0),
        (-110.0, 140.0),
        id="normal-moveable-with-offset",
    ),
]


class FakeText:
    def __init__(self):
        self.value = None

    def setText(self, value):
        self.value = value


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class FakeButton:
    def __init__(self):
        self.clicked = FakeSignal()

    def click(self):
        self.clicked.callback()


class FakeButtonBox:
    def __init__(self, dialog):
        self.dialog = dialog

    def addButton(self, text, role):
        self.dialog.reset_button = FakeButton()
        return self.dialog.reset_button


class FakeLayout:
    def addWidget(self, widget):
        self.widget = widget


class FakeDialog:
    def __init__(self):
        self.descLabel = FakeText()
        self.limitMin = FakeText()
        self.limitMax = FakeText()
        self.limitMinAbs = FakeText()
        self.limitMaxAbs = FakeText()
        self.buttonBox = FakeButtonBox(self)
        self.targetLayout = FakeLayout()
        self.rejected = False
        self.reset_button = None

    def exec(self):
        return devices.QDialog.DialogCode.Rejected

    def reject(self):
        self.rejected = True


class FakeClient:
    def __init__(self, params, param_info):
        self.params = params
        self.param_info = param_info

    def getDeviceParam(self, devname, param):
        return self.params[param]

    def getDeviceParamInfo(self, devname):
        return self.param_info


class FakeDevicePanel:
    def __init__(self):
        self.commands = []

    def exec_command(self, command):
        self.commands.append(command)


class FakeTarget:
    def setClient(self, client):
        self.client = client


def fmt(limits):
    return tuple(f"{limit:.1f}" for limit in limits)


def call_set_limits(monkeypatch, params, param_info, devrepr):
    dialog = FakeDialog()
    target = FakeTarget()
    client = FakeClient(params, param_info)
    device_panel = FakeDevicePanel()
    control_dialog = SimpleNamespace(
        devname="motor",
        devrepr=devrepr,
        client=client,
        devinfo=SimpleNamespace(fmtstr="%.1f"),
        device_panel=device_panel,
    )

    monkeypatch.setattr(devices, "dialogFromUi", lambda *args: dialog)
    monkeypatch.setattr(devices, "DeviceParamEdit", lambda *args, **kwargs: target)

    devices.ControlDialog.on_actionSetLimits_triggered(control_dialog)

    return dialog, device_panel


@pytest.mark.parametrize(
    ("offset", "diallimits", "userlimits", "hwuserlimits"),
    EPICS_MOTOR_LIMIT_CASES,
)
def test_hwuserlimits_are_displayed_as_absolute_range(
    monkeypatch, offset, diallimits, userlimits, hwuserlimits
):
    dialog, _device_panel = call_set_limits(
        monkeypatch,
        params={
            "userlimits": userlimits,
            "abslimits": diallimits,
            "offset": offset,
            "hwuserlimits": hwuserlimits,
        },
        param_info={
            "userlimits": {"userparam": True},
            "hwuserlimits": {"userparam": False},
        },
        devrepr="epicsmotor",
    )

    expected_userlimits = fmt(userlimits)
    expected_hwuserlimits = fmt(hwuserlimits)
    assert (dialog.limitMin.value, dialog.limitMax.value) == expected_userlimits
    assert (
        dialog.limitMinAbs.value,
        dialog.limitMaxAbs.value,
    ) == expected_hwuserlimits


def test_hwuserlimits_reset_sets_userlimits_to_hwuserlimits(monkeypatch):
    dialog, device_panel = call_set_limits(
        monkeypatch,
        params={
            "userlimits": (-90.0, 110.0),
            "abslimits": (-100.0, 150.0),
            "offset": -10.0,
            "hwuserlimits": (-110.0, 140.0),
        },
        param_info={
            "userlimits": {"userparam": True},
            "hwuserlimits": {"userparam": False},
        },
        devrepr="epicsmotor",
    )

    dialog.reset_button.click()

    assert device_panel.commands == [
        "set(epicsmotor, 'userlimits', (-110.0, 140.0))"
    ]
    assert dialog.rejected is True


@pytest.mark.parametrize(
    ("offset", "abslimits", "userlimits", "expected_abslimits"),
    MOVEABLE_LIMIT_CASES,
)
def test_normal_moveable_displays_absolute_limits(
    monkeypatch, offset, abslimits, userlimits, expected_abslimits
):
    dialog, _device_panel = call_set_limits(
        monkeypatch,
        params={
            "userlimits": userlimits,
            "abslimits": abslimits,
            "offset": offset,
        },
        param_info={
            "userlimits": {"userparam": True},
        },
        devrepr="normalmoveable",
    )

    expected_userlimits = fmt(userlimits)
    expected_abslimits = fmt(expected_abslimits)
    assert (dialog.limitMin.value, dialog.limitMax.value) == expected_userlimits
    assert (
        dialog.limitMinAbs.value,
        dialog.limitMaxAbs.value,
    ) == expected_abslimits


def test_normal_moveable_reset_still_calls_resetlimits(monkeypatch):
    dialog, device_panel = call_set_limits(
        monkeypatch,
        params={
            "userlimits": (-90.0, 120.0),
            "abslimits": (-100.0, 150.0),
            "offset": 10.0,
        },
        param_info={
            "userlimits": {"userparam": True},
        },
        devrepr="normalmoveable",
    )

    dialog.reset_button.click()

    assert device_panel.commands == ["resetlimits(normalmoveable)"]
    assert dialog.rejected is True

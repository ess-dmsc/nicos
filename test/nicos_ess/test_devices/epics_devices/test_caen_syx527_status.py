"""Power-supply status rules, independent of EPICS and the NICOS cache."""

from dataclasses import replace

import pytest

from nicos.core import status
from nicos_ess.devices.epics.caen_syx527 import SupplySnapshot


@pytest.fixture
def enabled_snapshot():
    return SupplySnapshot(
        voltages=(800.0, 800.0),
        setpoints=(800.0, 800.0),
        requested_on=2,
        enabled=2,
        ramping_up=0,
        ramping_down=0,
        alarm_status=(status.OK, ""),
    )


def evaluate(snapshot, **settings):
    request = dict(
        target=(800.0, 800.0),
        pending_power=None,
        precision=1.0,
        voltage_off_threshold=5.0,
        unit="V",
    )
    request.update(settings)
    return snapshot.status(**request)


@pytest.mark.parametrize(
    "changes, expected",
    [
        pytest.param({}, (status.OK, "output enabled"), id="enabled"),
        pytest.param(
            {"enabled": 1}, (status.BUSY, "1 of 2 outputs enabled"), id="enabling"
        ),
        pytest.param(
            {"requested_on": 1, "enabled": 1},
            (status.WARN, "1 of 2 outputs requested on"),
            id="mixed-power",
        ),
        pytest.param(
            {"ramping_up": 1}, (status.BUSY, "1 of 2 outputs ramping"), id="ramp-up"
        ),
        pytest.param(
            {"ramping_down": 1}, (status.BUSY, "1 of 2 outputs ramping"), id="ramp-down"
        ),
        pytest.param(
            {"setpoints": (800.0, 798.0)},
            (status.BUSY, "waiting for voltage setpoints to update"),
            id="setpoints",
        ),
        pytest.param(
            {"voltages": (800.0, 798.0)},
            (status.BUSY, "voltage readback has not reached target"),
            id="voltages",
        ),
        pytest.param(
            {"voltages": (799.0, 801.0)}, (status.OK, "output enabled"), id="precision"
        ),
    ],
)
def test_powered_output_states(enabled_snapshot, changes, expected):
    assert evaluate(replace(enabled_snapshot, **changes)) == expected


@pytest.mark.parametrize(
    "changes, threshold, expected",
    [
        pytest.param({}, 5.0, (status.DISABLED, "output disabled"), id="off"),
        pytest.param(
            {"enabled": 1},
            5.0,
            (status.BUSY, "waiting for outputs to disable"),
            id="still-on",
        ),
        pytest.param(
            {"ramping_up": 1},
            5.0,
            (status.BUSY, "waiting for outputs to disable"),
            id="still-ramping-up",
        ),
        pytest.param(
            {"ramping_down": 1, "voltages": (-5.0, 5.0)},
            5.0,
            (status.DISABLED, "output disabled"),
            id="safe-ramp-down",
        ),
        pytest.param(
            {"ramping_down": 1},
            None,
            (status.BUSY, "waiting for outputs to disable"),
            id="ramp-without-threshold",
        ),
        pytest.param(
            {"voltages": (-5.1, 0.0)},
            5.0,
            (status.BUSY, "waiting for output voltages to fall to 5 V or below"),
            id="voltage-above-threshold",
        ),
        pytest.param(
            {"voltages": (float("nan"), 0.0)},
            5.0,
            (status.BUSY, "waiting for output voltages to fall to 5 V or below"),
            id="invalid-voltage",
        ),
    ],
)
def test_shutdown_states(enabled_snapshot, changes, threshold, expected):
    off = replace(enabled_snapshot, requested_on=0, enabled=0, voltages=(0.0, 0.0))
    assert (
        evaluate(replace(off, **changes), voltage_off_threshold=threshold) == expected
    )


@pytest.mark.parametrize(
    "requested_on, pending_power, expected",
    [
        (0, True, (status.BUSY, "waiting for outputs to enable")),
        (1, True, (status.BUSY, "waiting for outputs to enable")),
        (2, False, (status.BUSY, "waiting for outputs to disable")),
        (2, True, (status.OK, "output enabled")),
    ],
)
def test_power_request_takes_priority_until_acknowledged(
    enabled_snapshot, requested_on, pending_power, expected
):
    snapshot = replace(enabled_snapshot, requested_on=requested_on)
    assert evaluate(snapshot, pending_power=pending_power) == expected


@pytest.mark.parametrize(
    "changes, alarm, expected",
    [
        ({}, status.WARN, (status.WARN, "EPICS alarm")),
        ({"ramping_up": 1}, status.WARN, (status.BUSY, "1 of 2 outputs ramping")),
        (
            {"requested_on": 0, "enabled": 0, "voltages": (0.0, 0.0)},
            status.WARN,
            (status.DISABLED, "output disabled"),
        ),
        (
            {"requested_on": 0, "enabled": 0, "voltages": (0.0, 0.0)},
            status.ERROR,
            (status.ERROR, "EPICS alarm"),
        ),
        (
            {"requested_on": 0, "enabled": 0, "voltages": (0.0, 0.0)},
            status.UNKNOWN,
            (status.UNKNOWN, "EPICS alarm"),
        ),
    ],
)
def test_status_and_message_come_from_the_same_nicos_level(
    enabled_snapshot, changes, alarm, expected
):
    snapshot = replace(enabled_snapshot, alarm_status=(alarm, "EPICS alarm"), **changes)
    assert evaluate(snapshot) == expected

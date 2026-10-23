import time

import pytest

from nicos.core import SIMULATION, status
from nicos.core.errors import (
    CommunicationError,
    ConfigurationError,
    MoveError,
    UsageError,
)
from nicos_ess.devices.epics.chopper import (
    SPEED_READBACK,
    SPEED_SETPOINT,
    EssChopper,
    EssT0Chopper,
)
from nicos_ess.devices.epics.pva import epics_common

ROOT = "SIM:CHOP:"
CHIC = "SIM:CHIC:"
STATES = [
    "Comms not ok",
    "Initialization",
    "Ready",
    "Rotating",
    "Coasting",
    "Stopping",
    "E. stopping",
]
READY, ROTATING, STOPPING = 2, 3, 5
PARK_COMMANDS = [
    "Null",
    "ParkOpen",
    "ParkClosed",
    "ParkSP",
    "DisablePark",
    "Delevitate",
]
PARK_TARGETS = {"ParkOpen": 277.83, "ParkClosed": 7.83}
T0_PARKS = ["Close", "Open", *(f"Window {i}" for i in range(1, 11))]


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(time, "time", clock)
    return clock


@pytest.fixture
def backend(fake_epics_backend_factory):
    backend = fake_epics_backend_factory(epics_common)
    enums = {
        f"{ROOT}ChopState_R": (STATES, READY),
        f"{ROOT}InPhaseTS-R": (["Not in phase", "In phase"], 0),
        f"{ROOT}ParkStatus_R": (["Unknown", "Not Parked", "Parking"], 1),
        f"{ROOT}OnSpd_R": (["Unknown", "Not on speed", "On speed"], 1),
        f"{CHIC}ConnectedR": (["Disconnected", "Connected"], 1),
        f"{ROOT}Lvl_Alrm": (["No Alarms", "Warnings", "Alarms", "Trip"], 0),
        f"{ROOT}CtrlMd_RB": (["Epics", "Chic", "Local"], 0),
        f"{ROOT}C_ExecuteUser": (["No request", "Start", "Stop", "Clear Alarms"], 0),
        f"{ROOT}C_Park": (PARK_COMMANDS, 0),
        f"{ROOT}ParkCmd_RB": (PARK_COMMANDS, 0),
        f"{ROOT}C_Execute": (
            ["Null", "Start", "Astart", "Stop", "Istop", "Coast", "ClearAlarm"],
            0,
        ),
        f"{ROOT}ParkPos_S": (T0_PARKS, 0),
        f"{ROOT}ParkPos_RB": (T0_PARKS, 0),
    }
    for pv, (choices, index) in enums.items():
        backend.values[pv] = index
        backend.value_choices[pv] = choices

    put = backend.put_pv_value
    backend.resets_statistics = True

    def put_like_the_ioc(pvname, value, wait=False):
        # evr_seq_calc >= 2.7.6: a new speed or delay drops InPhaseTS-R
        changed = backend.values.get(pvname) != value
        put(pvname, value, wait)
        resets = pvname in (f"{ROOT}{SPEED_SETPOINT}", f"{ROOT}ChopDly-S")
        if backend.resets_statistics and resets and changed:
            backend.emit_update(f"{ROOT}InPhaseTS-R", value=0)
        # the drive takes a park command and sets its new target, as YMIR's did
        if pvname == f"{ROOT}C_Park":
            backend.emit_update(f"{ROOT}ParkCmd_RB", value=PARK_COMMANDS.index(value))
            if value in PARK_TARGETS:
                backend.emit_update(f"{ROOT}ParkS_RB", value=PARK_TARGETS[value])
        elif pvname == f"{ROOT}Park_S":
            backend.emit_update(
                f"{ROOT}ParkCmd_RB", value=PARK_COMMANDS.index("ParkSP")
            )
            backend.emit_update(f"{ROOT}ParkS_RB", value=value)
        elif pvname == f"{ROOT}ParkPos_S":
            backend.emit_update(f"{ROOT}ParkPos_RB", value=T0_PARKS.index(value))

    backend.put_pv_value = put_like_the_ioc
    backend.values.update(
        {
            f"{ROOT}Log_R": "Ready: Entered state",
            f"{ROOT}Park_S": 0.0,
            f"{ROOT}TotDly": 0.0,
            f"{ROOT}Pos_R": 120.0,
            f"{ROOT}ParkS_RB": 120.0,
            f"{ROOT}DiffTSMean": 0.0,
            f"{ROOT}DiffTSStdDev": 0.0,
            f"{ROOT}DiffTSFWHMWidth": 0.0,
            f"{ROOT}DiffTSSamples": [],
            f"{ROOT}{SPEED_READBACK}": 0.0,
            f"{ROOT}{SPEED_SETPOINT}": 0.0,
            f"{ROOT}MaxSpd_R": 14.0,
            f"{ROOT}ChopDly-S": 0.0,
        }
    )
    return backend


@pytest.fixture
def disc(device_harness, backend, clock):
    daemon, _ = device_harness.create_pair(
        EssChopper,
        name="disc",
        shared={"pv_root": ROOT, "chic_root": CHIC},
    )
    return daemon


def emit(backend, suffix, value, root=ROOT):
    backend.emit_update(f"{root}{suffix}", value=value)


def puts(backend):
    return [(pv.removeprefix(ROOT), value) for pv, value, _ in backend.put_calls]


def spin(backend, speed):
    """The disc turns at the speed, in phase."""
    for suffix in (SPEED_SETPOINT, SPEED_READBACK):
        emit(backend, suffix, speed)
    emit(backend, "ChopState_R", ROTATING)
    emit(backend, "OnSpd_R", 2)
    emit(backend, "InPhaseTS-R", 1)


def run(device_harness, func, *args):
    return device_harness.run("daemon", func, *args)


def test_speed_is_the_pv_value(device_harness, backend, disc):
    emit(backend, SPEED_READBACK, 14.0)
    emit(backend, SPEED_SETPOINT, 14.0)

    assert run(device_harness, disc.speed.read) == 14.0
    assert run(device_harness, disc.speed.read, 0) == 14.0
    assert run(device_harness, disc.speed.doReadTarget) == 14.0
    assert run(device_harness, lambda: disc.speed.unit) == "Hz"


def test_starting_a_stopped_disc_writes_the_speed_then_start(
    device_harness, backend, disc
):
    run(device_harness, disc.speed.start, 14.0)

    assert puts(backend) == [(SPEED_SETPOINT, 14.0), ("C_ExecuteUser", "Start")]


def test_a_new_speed_on_a_turning_disc_writes_the_speed_then_start(
    device_harness, backend, disc
):
    spin(backend, 14.0)
    run(device_harness, disc.speed.start, 7.0)

    assert puts(backend) == [(SPEED_SETPOINT, 7.0), ("C_ExecuteUser", "Start")]


def test_speed_zero_stops_the_disc_and_completes_when_ready(
    device_harness, backend, disc
):
    spin(backend, 14.0)
    run(device_harness, disc.speed.start, 0.0)

    assert puts(backend) == [(SPEED_SETPOINT, 0.0), ("C_ExecuteUser", "Stop")]
    emit(backend, SPEED_SETPOINT, 0.0)
    emit(backend, "ChopState_R", STOPPING)
    assert not run(device_harness, disc.speed.isCompleted)
    emit(backend, "ChopState_R", READY)
    assert run(device_harness, disc.speed.isCompleted)


def settle(backend, speed):
    """The disc reaches the speed, in phase."""
    emit(backend, SPEED_READBACK, speed)
    emit(backend, "OnSpd_R", 2)
    emit(backend, "InPhaseTS-R", 1)


def test_a_move_completes_when_the_disc_is_in_phase_again(
    device_harness, backend, disc
):
    spin(backend, 7.0)
    run(device_harness, disc.speed.start, 14.0)
    # the IOC dropped InPhaseTS-R for the new setpoint, the disc is not there yet
    assert not run(device_harness, disc.speed.isCompleted)
    emit(backend, SPEED_READBACK, 14.0)
    assert not run(device_harness, disc.speed.isCompleted)
    emit(backend, "InPhaseTS-R", 1)
    assert run(device_harness, disc.speed.isCompleted)


def test_a_phase_move_completes_when_the_disc_is_in_phase_again(
    device_harness, backend, disc
):
    spin(backend, 14.0)
    assert run(device_harness, disc.phase.read) == 0.0
    run(device_harness, disc.phase.start, 90.0)
    assert not run(device_harness, disc.phase.isCompleted)
    emit(backend, "InPhaseTS-R", 1)
    assert run(device_harness, disc.phase.isCompleted)
    assert run(device_harness, disc.phase.read) == pytest.approx(90.0)


def test_a_move_waits_while_the_disc_is_off_speed(device_harness, backend, disc):
    spin(backend, 14.0)
    run(device_harness, disc.phase.start, 90.0)
    emit(backend, "OnSpd_R", 1)
    emit(backend, "InPhaseTS-R", 1)
    assert not run(device_harness, disc.phase.isCompleted)
    emit(backend, "OnSpd_R", 2)
    assert run(device_harness, disc.phase.isCompleted)


def test_a_direction_change_completes(device_harness, backend, disc):
    # YMIR's drive reads SpdS_RB +7 at -7 Hz: the move must not depend on it
    spin(backend, 7.0)
    run(device_harness, disc.speed.start, -7.0)
    emit(backend, "OnSpd_R", 1)
    emit(backend, SPEED_READBACK, -7.0)
    emit(backend, "OnSpd_R", 2)
    assert not run(device_harness, disc.speed.isCompleted)
    emit(backend, "InPhaseTS-R", 1)
    assert run(device_harness, disc.speed.isCompleted)


def test_a_move_does_not_complete_out_of_phase(device_harness, backend, disc):
    spin(backend, 14.0)
    run(device_harness, disc.phase.start, 90.0)
    assert not run(device_harness, disc.phase.isCompleted)
    assert not run(device_harness, disc.phase.isCompleted)


def test_a_move_fails_when_the_ioc_does_not_reset_its_statistics(
    device_harness, backend, disc
):
    backend.resets_statistics = False
    spin(backend, 14.0)

    with pytest.raises(MoveError, match="evr_seq_calc 2.7.6"):
        run(device_harness, disc.phase.start, 90.0)


def test_a_park_command_the_drive_does_not_take_says_so(device_harness, backend, disc):
    backend.put_pv_value = lambda pvname, value, wait=False: None

    with pytest.raises(MoveError, match="did not take the park command ParkOpen"):
        set_param(device_harness, disc, "park", "ParkOpen")


def test_a_lost_ioc_during_the_acknowledgement_is_a_communication_error(
    device_harness, backend, disc
):
    put = backend.put_pv_value

    def put_and_disconnect(pvname, value, wait=False):
        put(pvname, value, wait)
        backend.disconnect_backend()

    backend.put_pv_value = put_and_disconnect

    with pytest.raises(CommunicationError):
        set_param(device_harness, disc, "park_angle", 42.0)


def test_a_lost_ioc_connection_aborts_a_move(device_harness, backend, disc):
    spin(backend, 7.0)
    run(device_harness, disc.speed.start, 14.0)
    backend.disconnect_backend()

    with pytest.raises(MoveError):
        run(device_harness, disc.speed.isCompleted)
    with pytest.raises(MoveError):
        run(device_harness, disc.isCompleted)


def test_speed_and_phase_show_the_discs_lost_connection(device_harness, backend, disc):
    backend.disconnect_backend()

    for device in (disc, disc.speed, disc.phase):
        assert run(device_harness, device.status)[0] == status.UNKNOWN


def test_the_same_speed_on_a_steady_disc_writes_nothing(device_harness, backend, disc):
    spin(backend, 14.0)
    run(device_harness, disc.speed.start, 14.0)

    assert puts(backend) == []
    assert run(device_harness, disc.speed.isCompleted)


def test_repeating_an_interrupted_move_completes(device_harness, backend, disc):
    spin(backend, 7.0)
    run(device_harness, disc.speed.start, 14.0)
    assert not run(device_harness, disc.speed.isCompleted)
    # the script was stopped; the disc settled before the move was repeated
    settle(backend, 14.0)
    backend.put_calls.clear()
    run(device_harness, disc.speed.start, 14.0)

    assert puts(backend) == []
    assert run(device_harness, disc.speed.isCompleted)


def test_speed_above_the_maximum_is_refused(device_harness, backend, disc):
    allowed, why = run(device_harness, disc.speed.isAllowed, -28.0)
    assert run(device_harness, disc.speed.isAllowed, -14.0)[0]

    assert not allowed
    assert "14" in why


def test_phase_is_chopdly_at_the_target_speed(device_harness, backend, disc):
    emit(backend, SPEED_SETPOINT, 14.0)
    emit(backend, "ChopDly-S", 1e9 / 14 / 4)

    assert run(device_harness, disc.phase.read) == pytest.approx(90.0)
    assert run(device_harness, disc.phase.read, 0) == pytest.approx(90.0)
    assert run(device_harness, lambda: disc.phase.unit) == "deg"
    assert run(device_harness, lambda: disc.delay) == pytest.approx(1e9 / 56)

    run(device_harness, disc.phase.start, 180.0)
    assert puts(backend) == [("ChopDly-S", pytest.approx(1e9 / 14 / 2))]


def test_phase_needs_a_speed_and_a_range(device_harness, backend, disc):
    assert not run(device_harness, disc.phase.isAllowed, 90.0)[0]
    emit(backend, SPEED_SETPOINT, 14.0)
    assert run(device_harness, disc.phase.isAllowed, 90.0)[0]
    assert not run(device_harness, disc.phase.isAllowed, 360.0)[0]
    assert not run(device_harness, disc.phase.isAllowed, -1.0)[0]


def test_stopping_does_not_touch_the_disc(device_harness, backend, disc):
    spin(backend, 14.0)
    run(device_harness, disc.speed.stop)
    run(device_harness, disc.phase.stop)

    assert puts(backend) == []


@pytest.mark.parametrize(
    ("suffix", "value", "expected"),
    [
        ("ChopState_R", STOPPING, (status.BUSY, "Stopping")),
        ("InPhaseTS-R", 0, (status.BUSY, "not in phase")),
        ("Lvl_Alrm", 1, (status.WARN, "Warnings")),
        ("Lvl_Alrm", 3, (status.ERROR, "Trip")),
        ("CtrlMd_RB", 2, (status.WARN, "controlled from Local, not EPICS")),
    ],
)
def test_status(device_harness, backend, disc, suffix, value, expected):
    spin(backend, 14.0)
    emit(backend, "Log_R", "")
    assert run(device_harness, disc.status) == (status.OK, "")

    emit(backend, suffix, value)
    assert run(device_harness, disc.status) == expected
    assert run(device_harness, disc.speed.status) == expected
    assert run(device_harness, disc.phase.status) == expected


def test_status_shows_the_drives_last_message(device_harness, backend, disc):
    spin(backend, 14.0)
    emit(backend, "Log_R", "Rotation: In Phase")
    assert run(device_harness, disc.status) == (status.OK, "Rotation: In Phase")

    emit(backend, "Lvl_Alrm", 3)
    emit(backend, "Log_R", "Interlock: Vacuum lost")
    assert run(device_harness, disc.status) == (
        status.ERROR,
        "Trip; Interlock: Vacuum lost",
    )
    assert run(device_harness, disc.speed.status) == (
        status.ERROR,
        "Trip; Interlock: Vacuum lost",
    )


def test_status_without_the_chic(device_harness, backend, disc):
    emit(backend, "ConnectedR", 0, root=CHIC)

    assert run(device_harness, disc.status) == (
        status.ERROR,
        "no connection to the CHIC; Ready: Entered state",
    )


def test_ioc_values_are_parameters(device_harness, backend, disc):
    emit(backend, "TotDly", 1234.0)
    emit(backend, "DiffTSStdDev", 56.0)
    emit(backend, "InPhaseTS-R", 1)

    assert run(device_harness, lambda: disc.total_delay) == 1234.0
    assert run(device_harness, lambda: disc.delay_stddev) == 56.0
    assert run(device_harness, lambda: disc.in_phase) == "In phase"
    assert run(device_harness, lambda: disc.last_message) == "Ready: Entered state"
    assert run(device_harness, disc.read) == "Ready"


def set_param(device_harness, device, param, value):
    device_harness.run("daemon", setattr, device, param, value)


def test_commands_are_the_ioc_choices(device_harness, backend, disc):
    choices = run(device_harness, lambda: disc.parameters["command"].type.vals)
    assert choices == ("No request", "Start", "Stop", "Clear Alarms")

    set_param(device_harness, disc, "command", "Clear Alarms")
    assert puts(backend) == [("C_ExecuteUser", "Clear Alarms")]
    with pytest.raises(ConfigurationError):
        set_param(device_harness, disc, "command", "ClearAlarm")


def test_reset_clears_the_alarms_with_the_iocs_choice(device_harness, backend, disc):
    emit(backend, "Lvl_Alrm", 2)
    run(device_harness, disc.reset)

    assert puts(backend) == [("C_ExecuteUser", "Clear Alarms")]


def test_reset_without_alarms_sends_nothing(device_harness, backend, disc):
    # YMIR's drive answers "Command invalid in current state"
    run(device_harness, disc.reset)

    assert puts(backend) == []


def test_park(device_harness, backend, disc):
    set_param(device_harness, disc, "park", "ParkOpen")
    set_param(device_harness, disc, "park", "ParkClosed")
    set_param(device_harness, disc, "park_angle", 42.0)

    assert puts(backend) == [
        ("C_Park", "ParkOpen"),
        ("C_Park", "ParkClosed"),
        ("Park_S", 42.0),
    ]
    with pytest.raises(ConfigurationError):
        set_param(device_harness, disc, "park", "open")


def test_waiting_on_the_disc_waits_for_the_park_position(device_harness, backend, disc):
    # YMIR: the drive takes the command at once, reports Parking seconds later
    set_param(device_harness, disc, "park", "ParkClosed")
    assert not run(device_harness, disc.isCompleted)
    emit(backend, "Pos_R", 7.83)
    assert run(device_harness, disc.isCompleted)


def test_a_disc_at_its_park_target_is_parked_whatever_park_status_says(
    device_harness, backend, disc
):
    # YMIR's drive reaches the park and leaves ParkStatus_R at Parking
    set_param(device_harness, disc, "park", "ParkOpen")
    emit(backend, "ParkStatus_R", 2)
    assert run(device_harness, disc.status)[0] == status.BUSY
    emit(backend, "Pos_R", 277.82)
    assert run(device_harness, disc.status)[0] == status.OK
    assert run(device_harness, disc.isCompleted)


def test_a_disc_stopped_without_a_park_is_not_parking(device_harness, backend, disc):
    # after a stop, ParkS_RB reads 0 and the disc stays where it stopped
    emit(backend, "ParkS_RB", 0.0)
    emit(backend, "Pos_R", 346.3)

    assert run(device_harness, disc.status)[0] == status.OK


def test_parking_at_an_angle_waits_for_the_new_target(device_harness, backend, disc):
    set_param(device_harness, disc, "park_angle", 42.0)
    assert run(device_harness, disc.status)[0] == status.BUSY
    emit(backend, "Pos_R", 42.0)
    assert run(device_harness, disc.isCompleted)


def test_a_repeated_park_command_is_sent_again(device_harness, backend, disc):
    # YMIR: C_Park still holds ParkOpen after a park at an angle, and the drive
    # ignores a write that does not change it
    set_param(device_harness, disc, "park", "ParkOpen")
    set_param(device_harness, disc, "park_angle", 120.0)
    backend.put_calls.clear()
    set_param(device_harness, disc, "park", "ParkOpen")

    assert puts(backend) == [("C_Park", "Null"), ("C_Park", "ParkOpen")]


def test_a_repeated_start_is_sent_again(device_harness, backend, disc):
    # after an interlock stop, C_ExecuteUser still holds Start
    emit(backend, "C_ExecuteUser", 1)
    run(device_harness, disc.speed.start, 14.0)

    assert puts(backend) == [
        (SPEED_SETPOINT, 14.0),
        ("C_ExecuteUser", "No request"),
        ("C_ExecuteUser", "Start"),
    ]


def test_park_refuses_a_turning_disc(device_harness, backend, disc):
    spin(backend, 14.0)

    with pytest.raises(UsageError):
        set_param(device_harness, disc, "park", "ParkOpen")
    with pytest.raises(UsageError):
        set_param(device_harness, disc, "park_angle", 42.0)
    assert puts(backend) == []


@pytest.fixture
def t0(device_harness, backend, clock):
    daemon, _ = device_harness.create_pair(
        EssT0Chopper, name="t0", shared={"pv_root": ROOT, "chic_root": CHIC}
    )
    return daemon


def test_t0_parking_follows_park_status(device_harness, backend, t0):
    # the T0's ParkS_RB does not follow its park target
    set_param(device_harness, t0, "park", "Window 1")
    emit(backend, "ParkS_RB", 0.0)
    emit(backend, "ParkStatus_R", 2)
    assert run(device_harness, t0.status)[0] == status.BUSY
    emit(backend, "ParkStatus_R", 1)
    assert run(device_harness, t0.isCompleted)


def test_t0_commands_and_parking(device_harness, backend, t0):
    emit(backend, "Lvl_Alrm", 2)
    set_param(device_harness, t0, "park", "Close")
    set_param(device_harness, t0, "park", "Window 1")
    set_param(device_harness, t0, "park_angle", 42.0)
    run(device_harness, t0.speed.start, 14.0)
    run(device_harness, t0.speed.start, 0.0)
    run(device_harness, t0.reset)

    assert puts(backend) == [
        ("ParkPos_S", "Close"),
        ("ParkPos_S", "Window 1"),
        ("Park_S", 42.0),
        (SPEED_SETPOINT, 14.0),
        ("C_Execute", "Start"),
        (SPEED_SETPOINT, 0.0),
        ("C_Execute", "Stop"),
        ("C_Execute", "ClearAlarm"),
    ]


def test_a_dry_run_does_not_touch_the_ioc(device_harness, backend, clock):
    disc = device_harness.create(
        "daemon", EssChopper, name="dry", mode=SIMULATION, pv_root=ROOT, chic_root=CHIC
    )
    backend.get_calls.clear()

    with device_harness.activate("daemon") as active_session:
        active_session.setMode(SIMULATION)
        disc.speed.start(14.0)
        disc.phase.start(90.0)
        disc.park = "ParkOpen"
        disc.reset()
        assert backend.put_calls == []
        disc.speed.wait()
        disc.phase.wait()
        values = disc.speed.read(), disc.phase.read()

    assert values == (14.0, 90.0)
    assert backend.get_calls == []


def test_gui_info(device_harness, disc):
    info = run(device_harness, disc.get_chopper_gui_info)

    assert info["speed_key"] == "disc/speed_readback"
    assert info["park_angle_key"] == "disc/park_position"
    assert info["delay_errors_key"] == "disc/delay_errors"
    assert info["legacy_spd_sign"] is False

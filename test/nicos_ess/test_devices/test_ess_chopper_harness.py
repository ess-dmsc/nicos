import time

import pytest

from nicos import session
from nicos.core import SIMULATION, mixins, status
from nicos.core.errors import (
    CommunicationError,
    InvalidValueError,
    LimitError,
    MoveError,
    PositionError,
    UsageError,
)
from nicos_ess.devices.epics.chopper import (
    NO_COMMAND_HOLD,
    SPEED_READBACK,
    SPEED_SETPOINT,
    EssChopper,
    EssT0Chopper,
)
from nicos_ess.devices.epics.pva import epics_common
from test.nicos_ess.device_harness import UnitTestSession

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
DCU_STATES = [
    "Unknown",
    "Initialization",
    "Ready",
    "Idle/DCU off",
    "Run to speed",
    "Run to phase",
    "Rotating",
    "Coasting",
    "Stopping",
    "Interlock stopping",
    "Parking",
]
DCU_READY, DCU_PARKING = 2, 10
T0_PARKS = ["Close", "Open", *(f"Window {i}" for i in range(1, 11))]
SPEEDS = [-14, -7, 0, 7, 14]


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
        f"{ROOT}ParkStatus_R": (
            [
                "Unknown",
                "Not Parked",
                "Parking",
                "ParkedOpen",
                "ParkedClose",
                "ParkedSP",
            ],
            1,
        ),
        f"{ROOT}DcuState_R": (DCU_STATES, DCU_READY),
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
    backend.stops_on_zero_speed = True

    def put_like_the_ioc(pvname, value, wait=False):
        # evr_seq_calc >= 2.7.6: a new speed or delay drops InPhaseTS-R
        changed = backend.values.get(pvname) != value
        put(pvname, value, wait)
        resets = pvname in (f"{ROOT}{SPEED_SETPOINT}", f"{ROOT}ChopDly-S")
        if backend.resets_statistics and resets and changed:
            backend.emit_update(f"{ROOT}InPhaseTS-R", value=0)
        # YMIR's drive stops by itself on a speed setpoint of 0
        rotating = backend.values[f"{ROOT}ChopState_R"] == ROTATING
        stops = backend.stops_on_zero_speed and rotating and value == 0
        if pvname == f"{ROOT}{SPEED_SETPOINT}" and stops:
            backend.emit_update(f"{ROOT}ChopState_R", value=STOPPING)
        # the drive takes a park command and sets its new target, as YMIR's did
        if pvname == f"{ROOT}C_Park":
            backend.emit_update(f"{ROOT}ParkCmd_RB", value=PARK_COMMANDS.index(value))
            if value in PARK_TARGETS:
                backend.emit_update(f"{ROOT}ParkS_RB", value=PARK_TARGETS[value])
            elif value == "ParkSP":
                backend.emit_update(
                    f"{ROOT}ParkS_RB", value=backend.values[f"{ROOT}Park_S"]
                )
        elif pvname == f"{ROOT}Park_S" and changed:
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
        shared={"pv_root": ROOT, "chic_root": CHIC, "speeds": SPEEDS},
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

    assert puts(backend) == [(SPEED_SETPOINT, 0)]
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


def test_moving_the_disc_sets_the_speed_then_the_phase(device_harness, backend, disc):
    run(device_harness, disc.start, (14.0, 90.0))

    assert puts(backend) == [
        (SPEED_SETPOINT, 14.0),
        ("C_ExecuteUser", "Start"),
        ("ChopDly-S", pytest.approx(1e9 / 14 / 4)),
    ]
    assert not run(device_harness, disc.isCompleted)
    spin(backend, 14.0)
    assert run(device_harness, disc.isCompleted)
    assert run(device_harness, disc.read) == pytest.approx((14.0, 90.0))


def test_moving_the_disc_to_speed_zero_only_stops_it(device_harness, backend, disc):
    spin(backend, 14.0)
    run(device_harness, disc.start, (0.0, 90.0))

    assert puts(backend) == [(SPEED_SETPOINT, 0)]


def test_a_drive_that_keeps_turning_at_speed_zero_gets_stop(
    device_harness, backend, disc
):
    backend.stops_on_zero_speed = False
    spin(backend, 14.0)
    run(device_harness, disc.speed.start, 0.0)

    assert puts(backend) == [(SPEED_SETPOINT, 0), ("C_ExecuteUser", "Stop")]


def test_only_the_speeds_are_written_as_their_integers(device_harness, backend, disc):
    run(device_harness, disc.speed.start, 7.0)

    assert puts(backend) == [(SPEED_SETPOINT, 7), ("C_ExecuteUser", "Start")]
    assert type(puts(backend)[0][1]) is int
    for speed in (6.99, 7.5, 20.0):
        allowed, why = run(device_harness, disc.speed.isAllowed, speed)
        assert not allowed
        assert "[-14, -7, 0, 7, 14]" in why
        with pytest.raises(LimitError):
            run(device_harness, disc.speed.start, speed)
    assert not run(device_harness, disc.isAllowed, (6.98, 200.0))[0]


def test_the_disc_checks_speed_and_phase(device_harness, backend, disc):
    assert run(device_harness, disc.isAllowed, (14.0, 90.0))[0]
    assert run(device_harness, disc.isAllowed, (0.0, 400.0))[0]
    assert not run(device_harness, disc.isAllowed, (20.0, 90.0))[0]
    assert not run(device_harness, disc.isAllowed, (14.0, 360.0))[0]


def test_a_move_that_never_phases_in_times_out(
    device_harness, backend, disc, monkeypatch
):
    now = [1000.0]
    monkeypatch.setattr(mixins, "monotonic", lambda: now[0])
    spin(backend, 14.0)
    run(device_harness, disc.phase.start, 90.0)
    assert not run(device_harness, disc.phase.isCompleted)
    now[0] += 601
    with pytest.raises(PositionError, match="not done after 600 s: not in phase"):
        run(device_harness, disc.phase.isCompleted)


def test_a_finished_move_does_not_time_out_later(
    device_harness, backend, disc, monkeypatch
):
    now = [1000.0]
    monkeypatch.setattr(mixins, "monotonic", lambda: now[0])
    spin(backend, 14.0)
    run(device_harness, disc.phase.start, 90.0)
    emit(backend, "InPhaseTS-R", 1)
    assert run(device_harness, disc.phase.isCompleted)
    now[0] += 601
    emit(backend, "InPhaseTS-R", 0)
    assert not run(device_harness, disc.phase.isCompleted)


def test_waiting_for_a_park_times_out(device_harness, backend, disc, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(mixins, "monotonic", lambda: now[0])
    run(device_harness, disc.park, "ParkClosed")
    assert not run(device_harness, disc.isCompleted)
    now[0] += 601
    with pytest.raises(PositionError, match="parking"):
        run(device_harness, disc.isCompleted)


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
        run(device_harness, disc.park, "ParkOpen")


def test_a_lost_ioc_during_the_acknowledgement_is_a_communication_error(
    device_harness, backend, disc
):
    put = backend.put_pv_value

    def put_and_disconnect(pvname, value, wait=False):
        put(pvname, value, wait)
        backend.disconnect_backend()

    backend.put_pv_value = put_and_disconnect

    with pytest.raises(CommunicationError):
        run(device_harness, disc.position.start, 42.0)


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
    emit(backend, "MaxSpd_R", 7.0)
    allowed, why = run(device_harness, disc.speed.isAllowed, -14.0)
    assert run(device_harness, disc.speed.isAllowed, -7.0)[0]

    assert not allowed
    assert "maximum speed is 7.0" in why


def test_phase_is_chopdly_at_the_target_speed(device_harness, backend, disc):
    emit(backend, SPEED_SETPOINT, 14.0)
    emit(backend, "ChopDly-S", 1e9 / 14 / 4)

    assert run(device_harness, disc.phase.read) == pytest.approx(90.0)
    assert run(device_harness, disc.phase.read, 0) == pytest.approx(90.0)
    assert run(device_harness, lambda: disc.phase.unit) == "deg"

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
    assert run(device_harness, disc.status) == (status.OK, "Rotating")

    emit(backend, suffix, value)
    assert run(device_harness, disc.status) == expected
    assert run(device_harness, disc.speed.status) == expected
    assert run(device_harness, disc.phase.status) == expected


def test_status_shows_the_drives_last_message(device_harness, backend, disc):
    spin(backend, 14.0)
    emit(backend, "Log_R", "Rotation: In Phase")
    assert run(device_harness, disc.status) == (
        status.OK,
        "Rotating; Rotation: In Phase",
    )

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


def test_the_value_is_speed_and_phase(device_harness, backend, disc):
    spin(backend, 14.0)
    emit(backend, "ChopDly-S", 1e9 / 14 / 4)

    assert run(device_harness, disc.read) == pytest.approx((14.0, 90.0))
    assert run(device_harness, disc.read, 0) == pytest.approx((14.0, 90.0))
    assert (
        run(device_harness, disc.format, (14.0, 90.0), True) == "[14.00, 90.00] Hz deg"
    )
    assert [value.unit for value in run(device_harness, disc.valueInfo)] == [
        "Hz",
        "deg",
    ]

    emit(backend, SPEED_SETPOINT, 7.0)
    emit(backend, SPEED_READBACK, 7.0)
    assert run(device_harness, disc.read) == pytest.approx((7.0, 45.0))


def test_the_unit_and_format_replace_older_cached_ones(device_harness, backend, clock):
    # the disc's value used to be the state, with unit "" and fmtstr "%s"
    def cache_old_values():
        session.cache.put("stale", "unit", "")
        session.cache.put("stale", "fmtstr", "%s")

    device_harness.run("daemon", cache_old_values)
    disc = device_harness.create(
        "daemon",
        EssChopper,
        name="stale",
        pv_root=ROOT,
        chic_root=CHIC,
        speeds=SPEEDS,
    )

    assert run(device_harness, lambda: disc.unit) == "Hz deg"
    assert run(device_harness, lambda: disc.fmtstr) == "[%.2f, %.2f]"


def test_reset_clears_the_alarms_with_the_iocs_choice(device_harness, backend, disc):
    emit(backend, "Lvl_Alrm", 2)
    run(device_harness, disc.reset)

    assert puts(backend) == [("C_ExecuteUser", "Clear Alarms")]


def test_reset_without_alarms_sends_nothing(device_harness, backend, disc):
    # YMIR's drive answers "Command invalid in current state"
    run(device_harness, disc.reset)

    assert puts(backend) == []


def test_park(device_harness, backend, disc):
    run(device_harness, disc.park, "ParkOpen")
    run(device_harness, disc.park, "ParkClosed")
    run(device_harness, disc.position.start, 42.0)

    assert puts(backend) == [
        ("C_Park", "ParkOpen"),
        ("C_Park", "ParkClosed"),
        ("Park_S", 42.0),
    ]
    with pytest.raises(InvalidValueError):
        run(device_harness, disc.park, "open")
    choices = run(device_harness, lambda: disc.parameters["park_command"].type.vals)
    assert choices == tuple(PARK_COMMANDS)


def test_waiting_on_the_disc_waits_for_the_park_position(device_harness, backend, disc):
    # YMIR: the drive takes the command at once, reports Parking seconds later
    run(device_harness, disc.park, "ParkClosed")
    assert not run(device_harness, disc.isCompleted)
    emit(backend, "Pos_R", 7.83)
    assert run(device_harness, disc.isCompleted)


def test_a_disc_at_its_park_target_is_parked_whatever_park_status_says(
    device_harness, backend, disc
):
    # YMIR's drive reaches the park and leaves ParkStatus_R at Parking
    run(device_harness, disc.park, "ParkOpen")
    emit(backend, "ParkStatus_R", 2)
    assert run(device_harness, disc.status)[0] == status.BUSY
    emit(backend, "Pos_R", 277.82)
    assert run(device_harness, disc.status)[0] == status.OK
    assert run(device_harness, disc.isCompleted)


def test_the_disc_parks_until_the_drive_is_done(device_harness, backend, disc):
    # YMIR, 15:56:07: after a stop the drive parks at Park_S itself, and the
    # disc passed within the tolerance before the drive was Ready; a park
    # command sent then was ignored
    emit(backend, "ParkS_RB", 120.0)
    emit(backend, "DcuState_R", DCU_PARKING)
    emit(backend, "ParkStatus_R", 2)
    emit(backend, "Pos_R", 120.2)
    assert run(device_harness, disc.status) == (
        status.BUSY,
        "parking; Ready: Entered state",
    )
    assert not run(device_harness, disc.isCompleted)

    emit(backend, "DcuState_R", DCU_READY)
    assert run(device_harness, disc.isCompleted)


def test_a_parked_disc_is_not_parking_whichever_readback_sticks(
    device_harness, backend, disc
):
    emit(backend, "ParkS_RB", 120.0)
    emit(backend, "Pos_R", 120.0)
    # YMIR's Beckhoff drive: ParkStatus_R stays at Parking
    emit(backend, "ParkStatus_R", 2)
    assert run(device_harness, disc.status)[0] == status.OK
    # the SKF drives (DREAM OC-103): DcuState_R stays at Parking
    emit(backend, "DcuState_R", DCU_PARKING)
    emit(backend, "ParkStatus_R", 5)
    assert run(device_harness, disc.status)[0] == status.OK


def test_a_disc_stopped_without_a_park_is_not_parking(device_harness, backend, disc):
    # after a stop, ParkS_RB reads 0 and the disc stays where it stopped
    emit(backend, "ParkS_RB", 0.0)
    emit(backend, "Pos_R", 346.3)

    assert run(device_harness, disc.status)[0] == status.OK


def test_position_is_the_resolver_position(device_harness, backend, disc):
    emit(backend, "Pos_R", 61.8)

    assert run(device_harness, disc.position.read) == 61.8
    assert run(device_harness, lambda: disc.position.unit) == "deg"


def test_parking_at_an_angle_waits_for_the_new_target(device_harness, backend, disc):
    run(device_harness, disc.position.start, 42.0)
    assert run(device_harness, disc.status)[0] == status.BUSY
    assert not run(device_harness, disc.position.isCompleted)
    emit(backend, "Pos_R", 42.0)
    assert run(device_harness, disc.isCompleted)
    assert run(device_harness, disc.position.isCompleted)


def test_a_position_move_waits_for_the_precision(device_harness, backend, disc):
    # YMIR: the drive reports Ready 0.2-0.45 deg short of the target and the
    # disc creeps there over the next seconds
    run(device_harness, disc.position.start, 62.0)
    emit(backend, "Pos_R", 61.7)
    assert run(device_harness, disc.status)[0] == status.OK
    assert not run(device_harness, disc.position.isCompleted)
    emit(backend, "Pos_R", 61.93)
    assert run(device_harness, disc.position.isCompleted)


def test_a_position_move_completes_across_zero(device_harness, backend, disc):
    run(device_harness, disc.position.start, 0.0)
    emit(backend, "Pos_R", 359.95)

    assert run(device_harness, disc.position.isCompleted)


def test_a_position_above_359_is_not_allowed(device_harness, disc):
    assert run(device_harness, disc.position.isAllowed, 359.0)[0]
    assert not run(device_harness, disc.position.isAllowed, 359.5)[0]


def test_a_position_move_times_out(device_harness, backend, disc, monkeypatch):
    # after a park to 120 YMIR's disc sat 0.13-0.16 deg off for minutes
    now = [1000.0]
    monkeypatch.setattr(mixins, "monotonic", lambda: now[0])
    run(device_harness, disc.position.start, 120.5)
    emit(backend, "Pos_R", 120.35)
    assert not run(device_harness, disc.position.isCompleted)
    now[0] += 61
    with pytest.raises(PositionError):
        run(device_harness, disc.position.isCompleted)


def test_a_repeated_park_command_is_sent_again(device_harness, backend, disc):
    # YMIR: C_Park still holds ParkOpen after a park at an angle, and the drive
    # ignores a write that does not change it
    run(device_harness, disc.park, "ParkOpen")
    run(device_harness, disc.position.start, 120.0)
    backend.put_calls.clear()
    run(device_harness, disc.park, "ParkOpen")

    assert puts(backend) == [("C_Park", "Null"), ("C_Park", "ParkOpen")]


def test_parking_at_the_angle_park_s_holds_sends_park_sp(device_harness, backend, disc):
    # YMIR: Park_S already held 120 and the drive ignored writing it again
    run(device_harness, disc.position.start, 120.0)
    run(device_harness, disc.park, "ParkOpen")
    emit(backend, "Pos_R", 277.83)
    backend.put_calls.clear()
    run(device_harness, disc.position.start, 120.0)

    assert puts(backend) == [("C_Park", "ParkSP")]
    assert run(device_harness, disc.status)[0] == status.BUSY
    emit(backend, "Pos_R", 120.0)
    assert run(device_harness, disc.isCompleted)


def test_a_resent_command_holds_the_no_command_for_the_plc(
    device_harness, backend, disc, monkeypatch
):
    # YMIR, 16:48:55: Null and ParkOpen 3 ms apart, and the drive ignored it
    def delay(session, seconds):
        backend.put_calls.append(("delay", seconds, False))

    monkeypatch.setattr(UnitTestSession, "delay", delay)
    run(device_harness, disc.park, "ParkOpen")
    run(device_harness, disc.position.start, 120.0)
    backend.put_calls.clear()
    run(device_harness, disc.park, "ParkOpen")

    assert puts(backend) == [
        ("C_Park", "Null"),
        ("delay", NO_COMMAND_HOLD),
        ("C_Park", "ParkOpen"),
    ]


def test_a_repeated_start_is_sent_again(device_harness, backend, disc):
    # after an interlock stop, C_ExecuteUser still holds Start
    emit(backend, "C_ExecuteUser", 1)
    run(device_harness, disc.speed.start, 14.0)

    assert puts(backend) == [
        (SPEED_SETPOINT, 14.0),
        ("C_ExecuteUser", "No request"),
        ("C_ExecuteUser", "Start"),
    ]


def resend_start(device_harness, backend, choices):
    backend.value_choices[f"{ROOT}C_ExecuteUser"] = choices
    backend.values[f"{ROOT}C_ExecuteUser"] = choices.index("Start")
    disc, _ = device_harness.create_pair(
        EssChopper,
        name="disc",
        shared={"pv_root": ROOT, "chic_root": CHIC, "speeds": SPEEDS},
    )
    run(device_harness, disc.speed.start, 14.0)


def test_a_resent_command_finds_the_no_command_by_name(device_harness, backend, clock):
    resend_start(device_harness, backend, ["Coast", "Start", "Null", "Stop"])

    assert puts(backend) == [
        (SPEED_SETPOINT, 14.0),
        ("C_ExecuteUser", "Null"),
        ("C_ExecuteUser", "Start"),
    ]


def test_a_command_without_a_no_command_is_not_resent(device_harness, backend, clock):
    with pytest.raises(UsageError, match="no Null command to send Start again"):
        resend_start(device_harness, backend, ["Coast", "Start", "Stop"])

    assert puts(backend) == [(SPEED_SETPOINT, 14.0)]


def test_park_refuses_a_turning_disc(device_harness, backend, disc):
    spin(backend, 14.0)

    with pytest.raises(LimitError, match="stop the disc"):
        run(device_harness, disc.park, "ParkOpen")
    with pytest.raises(LimitError, match="stop the disc"):
        run(device_harness, disc.position.start, 42.0)
    assert puts(backend) == []


@pytest.fixture
def t0(device_harness, backend, clock):
    daemon, _ = device_harness.create_pair(
        EssT0Chopper,
        name="t0",
        shared={"pv_root": ROOT, "chic_root": CHIC, "speeds": SPEEDS},
    )
    return daemon


def test_t0_parking_follows_park_status(device_harness, backend, t0):
    # the T0's ParkS_RB does not follow its park target
    run(device_harness, t0.park, "Window 1")
    emit(backend, "ParkS_RB", 0.0)
    emit(backend, "ParkStatus_R", 2)
    assert run(device_harness, t0.status)[0] == status.BUSY
    emit(backend, "ParkStatus_R", 1)
    assert run(device_harness, t0.isCompleted)


def test_t0_commands_and_parking(device_harness, backend, t0):
    emit(backend, "Lvl_Alrm", 2)
    run(device_harness, t0.park, "Close")
    run(device_harness, t0.park, "Window 1")
    run(device_harness, t0.position.start, 42.0)
    run(device_harness, t0.speed.start, 14.0)
    run(device_harness, t0.speed.start, 0.0)
    run(device_harness, t0.reset)

    assert puts(backend) == [
        ("ParkPos_S", "Close"),
        ("ParkPos_S", "Window 1"),
        ("Park_S", 42.0),
        (SPEED_SETPOINT, 14.0),
        ("C_Execute", "Start"),
        (SPEED_SETPOINT, 0),
        ("C_Execute", "ClearAlarm"),
    ]


def test_a_dry_run_does_not_touch_the_ioc(device_harness, backend, clock):
    disc = device_harness.create(
        "daemon",
        EssChopper,
        name="dry",
        mode=SIMULATION,
        pv_root=ROOT,
        chic_root=CHIC,
        speeds=SPEEDS,
    )
    backend.get_calls.clear()

    with device_harness.activate("daemon") as active_session:
        active_session.setMode(SIMULATION)
        disc.start((14.0, 90.0))
        disc.speed.start(14.0)
        disc.phase.start(90.0)
        disc.park("ParkOpen")
        disc.position.start(42.0)
        disc.reset()
        assert backend.put_calls == []
        disc.wait()
        disc.speed.wait()
        disc.phase.wait()
        disc.position.wait()
        values = disc.speed.read(), disc.phase.read()

    assert values == (14.0, 90.0)
    assert backend.get_calls == []


def test_gui_info(device_harness, disc):
    info = run(device_harness, disc.get_chopper_gui_info)

    assert info["speed_key"] == "disc/speed_readback"
    assert info["park_angle_key"] == "disc/position"
    assert info["delay_errors_key"] == "disc/delay_errors"
    assert info["legacy_spd_sign"] is False

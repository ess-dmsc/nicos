from datetime import time

from nicos_ess.loki.devices.beamstop import (
    ArmPositions,
    XPositions,
)


class TestLokiBeamstopControllerHarness:
    def test_park_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Park all beamstops")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == XPositions.Parked
        assert devices["positioner_1"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_2"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_3"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_4"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_5"].read(maxage=0) == ArmPositions.Parked

    def test_monitor_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Monitor")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == XPositions.Pos1
        assert devices["positioner_1"].read(maxage=0) == ArmPositions.InBeam
        assert devices["positioner_2"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_3"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_4"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_5"].read(maxage=0) == ArmPositions.Parked

    def test_beamstop2_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 2")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == XPositions.Pos2
        assert devices["positioner_1"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_2"].read(maxage=0) == ArmPositions.InBeam
        assert devices["positioner_3"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_4"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_5"].read(maxage=0) == ArmPositions.Parked

    def test_beamstop_and_monitor_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 3 + monitor")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == XPositions.Pos3
        assert devices["positioner_1"].read(maxage=0) == ArmPositions.InBeam
        assert devices["positioner_2"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_3"].read(maxage=0) == ArmPositions.InBeam
        assert devices["positioner_4"].read(maxage=0) == ArmPositions.Parked
        assert devices["positioner_5"].read(maxage=0) == ArmPositions.Parked

    def test_sequence_park_all(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        controller_target = "Park all beamstops"
        sequence = devices["controller"]._generateSequence(controller_target)
        expected_step_1 = MockSeqDev(devices["positioner_x"], XPositions.Parked)
        expected_step_2 = [
            MockSeqDev(devices["positioner_1"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_2"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_3"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_4"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_5"], ArmPositions.Parked),
        ]
        assert sequence_as_expected(
            sequence,
            [
                expected_step_1,
                expected_step_2,
            ],
        )

    def test_sequence_select_monitor(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        controller_target = "Monitor"
        sequence = devices["controller"]._generateSequence(controller_target)
        expected_step_1 = MockSeqDev(devices["positioner_x"], XPositions.Parked)
        expected_step_2 = [
            MockSeqDev(devices["positioner_1"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_2"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_3"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_4"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_5"], ArmPositions.Parked),
        ]
        expected_step_3 = MockSeqDev(devices["positioner_1"], ArmPositions.InBeam)
        expected_step_4 = MockSeqDev(devices["positioner_y"], "In beam")
        expected_step_5 = MockSeqDev(devices["positioner_x"], XPositions.Pos1)
        assert sequence_as_expected(
            sequence,
            [
                expected_step_1,
                expected_step_2,
                expected_step_3,
                expected_step_4,
                expected_step_5,
            ],
        )

    def test_sequence_select_monitor_and_beamstop(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        controller_target = "Beamstop 4 + monitor"
        sequence = devices["controller"]._generateSequence(controller_target)
        expected_step_1 = MockSeqDev(devices["positioner_x"], XPositions.Parked)
        expected_step_2 = [
            MockSeqDev(devices["positioner_1"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_2"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_3"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_4"], ArmPositions.Parked),
            MockSeqDev(devices["positioner_5"], ArmPositions.Parked),
        ]
        expected_step_3 = MockSeqDev(devices["positioner_4"], ArmPositions.Intermediate)
        expected_step_4 = [
            MockSeqDev(devices["positioner_1"], ArmPositions.InBeam),
            MockSeqDev(devices["positioner_4"], ArmPositions.InBeam),
        ]
        expected_step_5 = MockSeqDev(devices["positioner_y"], "In beam")
        expected_step_6 = MockSeqDev(devices["positioner_x"], XPositions.Pos4)

        assert sequence_as_expected(
            sequence,
            [
                expected_step_1,
                expected_step_2,
                expected_step_3,
                expected_step_4,
                expected_step_5,
                expected_step_6,
            ],
        )

    def test_sequence_add_monitor_if_beamstop_is_already_down(
        self, loki_beamstop_setup
    ):
        devices = loki_beamstop_setup
        controller_value = "Beamstop 2"
        devices["controller"].move(controller_value)
        devices["controller"].wait()
        assert devices["controller"].read(maxage=0) == "Beamstop 2"

        controller_target = "Beamstop 2 + monitor"
        sequence = devices["controller"]._generateSequence(controller_target)
        expected_step = MockSeqDev(devices["positioner_1"], ArmPositions.InBeam)
        assert sequence_as_expected(sequence, [expected_step])

    def test_sequence_change_beamstop(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        controller_value = "Beamstop 2"
        devices["controller"].move(controller_value)
        devices["controller"].wait()
        assert devices["controller"].read(maxage=0) == "Beamstop 2"

        controller_target = "Beamstop 3"
        sequence = devices["controller"]._generateSequence(controller_target)
        expected_step_1 = MockSeqDev(devices["positioner_x"], XPositions.Parked)
        expected_step_2 = MockSeqDev(devices["positioner_2"], ArmPositions.Parked)
        expected_step_3 = MockSeqDev(devices["positioner_3"], ArmPositions.InBeam)
        expected_step_4 = MockSeqDev(devices["positioner_y"], "In beam")
        expected_step_5 = MockSeqDev(devices["positioner_x"], XPositions.Pos3)

        assert sequence_as_expected(
            sequence,
            [
                expected_step_1,
                expected_step_2,
                expected_step_3,
                expected_step_4,
                expected_step_5,
            ],
        )


class MockSeqDev:
    def __init__(self, dev, target):
        self.dev = dev
        self.target = target

    def __repr__(self):
        return f"{self.dev} -> {self.target}"

    def __eq__(self, other):
        return self.dev == other.dev and self.target == other.target


def device_name(seqdev):
    return seqdev.dev.name


def sequence_as_expected(sequence, expected_steps):
    if len(sequence) != len(expected_steps):
        return False
    for i, step in enumerate(expected_steps):
        if isinstance(step, MockSeqDev):
            if step != sequence[i]:
                return False
        else:
            ordered_seq = sorted(sequence[i], key=device_name)
            ordered_steps = sorted(step, key=device_name)
            if ordered_seq != ordered_steps:
                return False
    return True

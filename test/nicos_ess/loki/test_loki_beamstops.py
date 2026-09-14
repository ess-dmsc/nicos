class TestLokiBeamstopControllerHarness:
    def test_park_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Park all beamstops")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == "parked"
        assert devices["positioner_1"].read(maxage=0) == "parked"
        assert devices["positioner_2"].read(maxage=0) == "parked"
        assert devices["positioner_3"].read(maxage=0) == "parked"
        assert devices["positioner_4"].read(maxage=0) == "parked"
        assert devices["positioner_5"].read(maxage=0) == "parked"

    def test_monitor_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 1")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == "xpos bs1"
        assert devices["positioner_1"].read(maxage=0) == "in-beam"
        assert devices["positioner_2"].read(maxage=0) == "parked"
        assert devices["positioner_3"].read(maxage=0) == "parked"
        assert devices["positioner_4"].read(maxage=0) == "parked"
        assert devices["positioner_5"].read(maxage=0) == "parked"

    def test_beamstop2_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 2")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == "xpos bs2"
        assert devices["positioner_1"].read(maxage=0) == "parked"
        assert devices["positioner_2"].read(maxage=0) == "in-beam"
        assert devices["positioner_3"].read(maxage=0) == "parked"
        assert devices["positioner_4"].read(maxage=0) == "parked"
        assert devices["positioner_5"].read(maxage=0) == "parked"

    def test_beamstop_and_monitor_positions(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 3 + monitor")
        devices["controller"].wait()
        assert devices["positioner_x"].read(maxage=0) == "xpos bs3"
        assert devices["positioner_1"].read(maxage=0) == "in-beam"
        assert devices["positioner_2"].read(maxage=0) == "parked"
        assert devices["positioner_3"].read(maxage=0) == "in-beam"
        assert devices["positioner_4"].read(maxage=0) == "parked"
        assert devices["positioner_5"].read(maxage=0) == "parked"

    def test_sequence_park_all(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 1")
        controller_target = "Park all beamstops"
        sequence = devices["controller"]._generateSequence(controller_target)

        expected_step_1 = MockSeqDev(devices["positioner_x"], "parked")
        expected_step_2 = MockSeqDev(devices["positioner_y"], "in-beam")
        expected_step_3 = [
            MockSeqDev(devices["positioner_1"], "parked"),
            MockSeqDev(devices["positioner_2"], "parked"),
            MockSeqDev(devices["positioner_3"], "parked"),
            MockSeqDev(devices["positioner_4"], "parked"),
            MockSeqDev(devices["positioner_5"], "parked"),
        ]

        assert sequence_as_expected(
            sequence,
            [
                expected_step_1,
                expected_step_2,
                expected_step_3,
            ],
        )

    def test_sequence_select_monitor(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 2")
        controller_target = "Beamstop 1"
        sequence = devices["controller"]._generateSequence(controller_target)

        expected_step_1 = MockSeqDev(devices["positioner_x"], "parked")
        expected_step_2 = MockSeqDev(devices["positioner_y"], "in-beam")
        expected_step_3 = [
            MockSeqDev(devices["positioner_1"], "parked"),
            MockSeqDev(devices["positioner_2"], "parked"),
            MockSeqDev(devices["positioner_3"], "parked"),
            MockSeqDev(devices["positioner_4"], "parked"),
            MockSeqDev(devices["positioner_5"], "parked"),
        ]
        expected_step_4 = [
            MockSeqDev(devices["positioner_1"], "in-beam"),
            MockSeqDev(devices["positioner_2"], "parked"),
            MockSeqDev(devices["positioner_3"], "parked"),
            MockSeqDev(devices["positioner_4"], "parked"),
            MockSeqDev(devices["positioner_5"], "parked"),
        ]
        expected_step_5 = MockSeqDev(devices["positioner_y"], "in-beam")
        expected_step_6 = MockSeqDev(devices["positioner_x"], "xpos bs1")
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

    def test_sequence_select_monitor_and_beamstop(self, loki_beamstop_setup):
        devices = loki_beamstop_setup
        devices["controller"].move("Beamstop 3")
        controller_target = "Beamstop 4 + monitor"
        sequence = devices["controller"]._generateSequence(controller_target)
        expected_step_1 = MockSeqDev(devices["positioner_x"], "parked")
        expected_step_2 = MockSeqDev(devices["positioner_y"], "in-beam")
        expected_step_3 = [
            MockSeqDev(devices["positioner_1"], "parked"),
            MockSeqDev(devices["positioner_2"], "parked"),
            MockSeqDev(devices["positioner_3"], "parked"),
            MockSeqDev(devices["positioner_4"], "parked"),
            MockSeqDev(devices["positioner_5"], "parked"),
        ]
        expected_step_4 = [
            MockSeqDev(devices["positioner_1"], "in-beam"),
            MockSeqDev(devices["positioner_2"], "parked"),
            MockSeqDev(devices["positioner_3"], "parked"),
            MockSeqDev(devices["positioner_4"], "in-beam"),
            MockSeqDev(devices["positioner_5"], "parked"),
        ]
        expected_step_5 = MockSeqDev(devices["positioner_y"], "in-beam")
        expected_step_6 = MockSeqDev(devices["positioner_x"], "xpos bs4")

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

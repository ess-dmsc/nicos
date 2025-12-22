includes = ["stdsystem"]

devices = dict(
    restricted_motor=device(
        "test.nicos_ess.loki.test_loki_detector_carriage.FakeLokiDetectorMotion",
        motorpv="IOC:m1",
        ps_bank_name="ps_bank_hv",
        voltage_off_threshold=5.0,
    ),
)
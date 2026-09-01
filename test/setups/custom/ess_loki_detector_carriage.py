includes = ["stdsystem"]

devices = dict(
    restricted_motor=device(
        "test.nicos_ess.loki.test_loki_detector_carriage.FakeLokiDetectorMotion",
        motorpv="IOC:m1",
        power_supply="ps_bank_hv",
        has_powerauto=False,
        has_msgtxt=False,
        has_errorbit=False,
        has_reseterror=False,
    ),
)

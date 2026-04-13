# Minimal area-detector setup used by command tests.
#
# One image channel is wrapped in an aggregate detector so the tests can verify
# how generic NICOS `count()` and `scan()` interact with the simplified ESS
# area-detector classes.
includes = ["ess_count_scan_common"]

devices = dict(
    ad_1=device(
        "nicos_ess.devices.epics.area_detector.AreaDetector",
        pv_root="SIM:AD:",
        image_pv="SIM:AD:IMAGE",
        pva=True,
    ),
    ad_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        images=["ad_1"],
        timers=["timer"],
    ),
)

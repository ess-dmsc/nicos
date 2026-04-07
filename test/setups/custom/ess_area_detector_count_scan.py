includes = ["stdsystem"]

devices = dict(
    axis=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-10, 10),
        curvalue=0,
        unit="mm",
        fmtstr="%.2f",
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        unit="s",
        fmtstr="%.2f",
        update_interval=0.01,
    ),
    ad_1=device(
        "test.nicos_ess.test_commands.test_area_detector_count_scan.CountingFakeAreaDetector",
        pv_root="TEST",
        image_pv="TEST_IMAGE",
    ),
    ad_collector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        images=["ad_1"],
        timers=["timer"],
    ),
)

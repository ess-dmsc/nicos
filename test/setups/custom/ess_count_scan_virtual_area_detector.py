includes = ["axis"]

devices = dict(
    area_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        fmtstr="%.2f",
        unit="s",
        update_interval=0.01,
    ),
    camera=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetector",
        acquiretime=0.01,
        acquireperiod=0.01,
        sizex=32,
        sizey=32,
    ),
    area_detector=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetectorCollector",
        timers=["area_timer"],
        images=["camera"],
    ),
)

includes = ["axis"]

devices = dict(
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        visibility=(),
    ),
    timedet=device(
        "nicos.devices.generic.Detector",
        timers=["timer"],
    ),
    camera=device(
        "nicos_ess.devices.epics.area_detector.AreaDetector",
        pv_root="SIM:AD:",
        image_pv="SIM:AD:IMAGE",
    ),
    area_detector=device(
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        images=["camera"],
    ),
)

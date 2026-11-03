# ruff: noqa: F821
description = "A virtual area detector setup."

devices = dict(
    camera=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetector",
        description="A virtual camera.",
        unit="images",
        pollinterval=None,
    ),
    image_type=device(
        "nicos_ess.devices.epics.area_detector.ImageType",
        description="Image type for the tomography.",
    ),
    area_detector=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(area_detector)
camera.doSetPreset(n=1)
area_detector.doSetPreset(camera=1)
"""

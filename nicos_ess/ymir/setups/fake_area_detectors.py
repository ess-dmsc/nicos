# ruff: noqa: F821
description = "A virtual area detector setup."

devices = dict(
    virtual_camera=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetector",
        description="A virtual camera.",
        unit="images",
        pollinterval=None,
    ),
    virtual_image_type=device(
        "nicos_ess.devices.epics.area_detector.ImageType",
        description="Image type for the tomography.",
    ),
    virtual_area_detector_collector=device(
        "nicos_ess.devices.virtual.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["virtual_camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(virtual_area_detector_collector)
virtual_camera.doSetPreset(n=1)
virtual_area_detector_collector.doSetPreset(virtual_camera=1)
"""

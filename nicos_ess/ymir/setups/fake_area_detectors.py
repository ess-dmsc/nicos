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
        "nicos_ess.devices.image_type.ImageType",
        description="Image type for the tomography.",
    ),
    virtual_area_detector_collector=device(
        "nicos.devices.generic.Detector",
        description="Area detector collector",
        images=["virtual_camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

startupcode = """
SetDetectors(virtual_area_detector_collector)
virtual_area_detector_collector.setPreset(virtual_camera=1)
"""

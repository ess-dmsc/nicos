# ruff: noqa: F821

description = "ADSimDetector"

camera_system_pv_root = "13SIM1:"
camera_device_pv_root = "cam1:"
camera_ndplugin_pv_root = "image1:"

devices = dict(
    ad_sim_detector=device(
        "nicos_ess.devices.epics.adcore.AreaDetector",
        description="Simulated detector data",
        pv_root=f"{camera_system_pv_root}{camera_device_pv_root}",
        image_pv_root=f"{camera_system_pv_root}{camera_ndplugin_pv_root}",
        pva=True,
        monitor=True,
        pollinterval=0.5,
    ),
    ad_sim_detector_collector=device(
        "nicos.devices.generic.Detector",
        description="Area detector collector",
        images=["ad_sim_detector"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

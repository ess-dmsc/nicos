# ruff: noqa: F821

description = "ADSimDetector"

camera_system_pv_root = "13SIM1:"
camera_device_pv_root = "cam1:"
camera_ndplugin_pv_root = "image1:"

devices = dict( 
    ad_sim_detector=device(
        "nicos_ess.devices.epics.area_detector.ADSimDetector",
        description="Simulated detector data.",
        pv_root=f"{camera_system_pv_root}{camera_device_pv_root}",
        image_pv=f"{camera_system_pv_root}{camera_ndplugin_pv_root}ArrayData", ####the image comes from this
        unit="images",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    ad_sim_detector_area_detector_collector=device( 
        "nicos_ess.devices.epics.area_detector.AreaDetectorCollector",
        description="Area detector collector",
        images=["orca_camera"],
        liveinterval=1,
        pollinterval=1,
        unit="",
    ),
)

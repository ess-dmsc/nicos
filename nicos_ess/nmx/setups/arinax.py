description = "ARINAX controls"

group = "optional"

devices = dict(
    # Backlight
    backlight_level=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="ARINAX Backlight Level",
        readpv="NMX:BackLightLevel",
        writepv="NMX:BackLightLevel",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    backlight_position=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="ARINAX Backlight Position",
        readpv="NMX:BackLightPOS",
        writepv="NMX:BackLightPOS",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    # Zoom
    zoom_level=device(
        "nicos_ess.devices.epics.pva.EpicsDigitalMoveable",
        description="ARINAX Zoom Level",
        readpv="NMX:ZoomLevel",
        writepv="NMX:ZoomLevel",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    zoom_range=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="ARINAX Zoom Range",
        readpv="NMX:getZoomRange",
        writepv="NMX:getZoomRange",
        pva=False,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
)

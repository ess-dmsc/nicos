# ruff: noqa: F821

description = "Hamamatsu light intensifier"

pv_root = "YMIR-Det1:NDet-GInt-001:"

devices = dict(
    hama_pmt_value=device(
        "nicos.devices.epics.pva.EpicsReadable",
        description="The current value of the intensifier",
        readpv=f"{pv_root}IntensifierValue-R",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    hama_pmt_status=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The status of the intensifier",
        readpv=f"{pv_root}Status-R",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
    hama_pmt_gain=device(
        "nicos.devices.epics.pva.EpicsDigitalMoveable",
        description="The gain of the intensifier",
        readpv=f"{pv_root}IntensifierGain-R",
        writepv=f"{pv_root}IntensifierGain-S",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
    hama_pmt_connection=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The connection status of the intensifier",
        readpv=f"{pv_root}DeviceConnected-R",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
    hama_pmt=device(
        "nicos_ess.devices.epics.hama_intensifier.HamaIntensifierController",
        description="The control of the intensifier",
        readpv=f"{pv_root}OperationCtrl-R",
        writepv=f"{pv_root}OperationCtrl-S",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        status="hama_pmt_status",
        connection="hama_pmt_connection",
        gain="hama_pmt_gain",
        value="hama_pmt_value",
        mode="hama_pmt_mode",
    ),
    hama_pmt_mode=device(
        "nicos.devices.epics.pva.EpicsMappedMoveable",
        description="The operation mode of the intensifier",
        readpv=f"{pv_root}OperationMode-R",
        writepv=f"{pv_root}OperationMode-R",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility=(),
    ),
)

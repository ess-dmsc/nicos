# ruff: noqa: F821

description = "Hamamatsu light intensifier"

hama_root = "ODIN-DtCMOS:NDet-ImgInt-002:"
gate_root = "ODIN-DtCmn:Ctrl-EVR-001:"

devices = dict(
    hama_pmt_value=device(
        "nicos.devices.epics.pva.EpicsReadable",
        description="The current value of the intensifier",
        readpv=f"{hama_root}IntensifierValue-R",
    ),
    hama_pmt_status=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The status of the intensifier",
        readpv=f"{hama_root}Status-R",
        visibility=(),
    ),
    hama_pmt_gain=device(
        "nicos.devices.epics.pva.EpicsDigitalMoveable",
        description="The gain of the intensifier",
        readpv=f"{hama_root}IntensifierGain-R",
        writepv=f"{hama_root}IntensifierGain-S",
        visibility=(),
    ),
    hama_pmt_connection=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The connection status of the intensifier",
        readpv=f"{hama_root}DeviceConnected-R",
        visibility=(),
    ),
    hama_pmt=device(
        "nicos.devices.epics.hama_intensifier.HamaIntensifierController",
        description="The control of the intensifier",
        readpv=f"{hama_root}OperationCtrl-R",
        writepv=f"{hama_root}OperationCtrl-S",
        status="hama_pmt_status",
        connection="hama_pmt_connection",
        gain="hama_pmt_gain",
        value="hama_pmt_value",
        mode="hama_pmt_mode",
    ),
    hama_pmt_mode=device(
        "nicos.devices.epics.pva.EpicsMappedMoveable",
        description="The operation mode of the intensifier",
        readpv=f"{hama_root}OperationMode-R",
        writepv=f"{hama_root}OperationMode-S",
        visibility=(),
    ),
    gate_delay=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The delay of the gate",
        readpv=f"{gate_root}DlyGen0Delay-RB",
        writepv=f"{gate_root}DlyGen0Delay-SP",
        abslimits=(0, 71400),
        userlimits=(0, 71400),
        precision=0.1,
    ),
    gate_width=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The width of the gate",
        readpv=f"{gate_root}DlyGen0Width-RB",
        writepv=f"{gate_root}DlyGen0Width-SP",
        abslimits=(0, 71400),
        userlimits=(0, 71400),
        precision=0.1,
    ),
)

description = "Setup for the Arinax Rapid Nozzle Exchange (REx) system."

pv_root = "LabS-SEE3:SE-REX-01:"

devices = dict(
    nozzle_switcher=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Nozzle Switcher",
        readpv=f"{pv_root}ActualPosInterpret",
        writepv=f"{pv_root}SetPosition",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    nozzle_switcher_error=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Status of the Nozzle Switcher",
        readpv=f"{pv_root}ErrorState-RB",
    ),
    nozzle_switcher_state=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Status of the Nozzle Switcher",
        readpv=f"{pv_root}RunMode-RB",
    ),
    nozzle_switcher_motion_time=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Time for the Nozzle Switcher motion",
        readpv=f"{pv_root}LastMotionTime-RB",
    ),
    nozzle_switcher_set_timeout=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Timeout for the Nozzle Switcher motion",
        readpv=f"{pv_root}MotionTimeout-RB",
        writepv=f"{pv_root}SetMotionTimeout-SP",
    ),
)

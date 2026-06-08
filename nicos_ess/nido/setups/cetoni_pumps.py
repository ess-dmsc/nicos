description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"
pump2_pvroot = "B02-CSLab:SE-Pumps:SP2"
linked_pvroot = "B02-CSLab:SE-Pumps:Lnkd"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Control device for cetoni pump SP1",
        pvroot=pump1_pvroot,
    ),
    pump1_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Device to set the configuration of cetoni pump SP1",
        readpv=f"{pump1_pvroot}SyrType-SP",
        writepv=f"{pump1_pvroot}SyrType-SP",
    ),
    pump2=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Control device for cetoni pump SP2",
        pvroot=pump2_pvroot,
    ),
    pump2_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Device to set the configuration of cetoni pump SP2",
        readpv=f"{pump2_pvroot}SyrType-SP",
        writepv=f"{pump2_pvroot}SyrType-SP",
    ),
    linked_pumping_control=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpLinkedMode",
        pvroot="",
        sp1="pump1",
        sp2="pump2",
        pump_time="linked_pumping_time",
    ),
    linked_pumping_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Device to set the configuration of cetoni pump SP2",
        readpv=f"{linked_pvroot}StopMode-SP",
        writepv=f"{linked_pvroot}StopMode-SP",
    ),
    linked_pumping_time=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsDigitalMoveable",
        readpv=f"{linked_pvroot}MaxDosingTime-SP",
        writepv=f"{linked_pvroot}MaxDosingTime-SP",
    ),
)

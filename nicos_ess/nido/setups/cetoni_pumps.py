description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"
pump2_pvroot = "B02-CSLab:SE-Pumps:SP2"
linked_pvroot = "B02-CSLab:SE-Pumps:Lnkd"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Control device for cetoni pump SP1",
        pvroot=pump1_pvroot,
        linked_pump_device="linked_pumping",
        home_warning_msg="Please make sure syringes are removed before homing",
    ),
    pump1_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Device to set the configuration of cetoni pump SP1",
        readpv=f"{pump1_pvroot}SyrType",
        writepv=f"{pump1_pvroot}SyrType",
    ),
    pump2=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Control device for cetoni pump SP2",
        pvroot=pump2_pvroot,
        linked_pump_device="linked_pumping",
        home_warning_msg="Please make sure syringes are removed before homing",
    ),
    pump2_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Device to set the configuration of cetoni pump SP2",
        readpv=f"{pump2_pvroot}SyrType",
        writepv=f"{pump2_pvroot}SyrType",
    ),
    linked_pumping=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpLinkedMode",
        description="Device to start the linked pumping flow",
        pvroot=linked_pvroot,
        linked_pumping_mode="linked_pumping_mode",
    ),
    linked_pumping_mode=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Device to set the linked pumping mode",
        readpv=f"{linked_pvroot}StopMode-SP",
        writepv=f"{linked_pvroot}StopMode-SP",
    ),
    linked_pumping_time=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsDigitalMoveable",
        description="Device to set the time for linked pumping in time mode",
        readpv=f"{linked_pvroot}MaxDosingTime-SP",
        writepv=f"{linked_pvroot}MaxDosingTime-SP",
    ),
)

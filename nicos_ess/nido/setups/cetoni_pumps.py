description = "The cetoni pumps"

pvroot = "B02-CSLab:SE-Pumps:"
pump1_pvroot = f"{pvroot}SP1"
pump2_pvroot = f"{pvroot}SP2"
linked_pvroot = f"{pvroot}Lnkd"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Control device for cetoni pump SP1",
        pvroot=pvroot,
        pump_pvroot=pump1_pvroot,
        readpv=f"{pump1_pvroot}FilledVolume",
        writepv=f"{pump1_pvroot}FillVol-SP",
        home_warning_msg="Please make sure syringes are removed before homing",
        precision=0.00001,
        linked_pumping="linked_pumping",
    ),
    pump2=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Control device for cetoni pump SP2",
        pvroot=pvroot,
        pump_pvroot=pump2_pvroot,
        readpv=f"{pump2_pvroot}FilledVolume",
        writepv=f"{pump2_pvroot}FillVol-SP",
        home_warning_msg="Please make sure syringes are removed before homing",
        precision=0.00001,
        linked_pumping="linked_pumping",
    ),
    linked_pumping=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpLinkedMode",
        description="Device to start the linked pumping flow",
        pvroot=linked_pvroot,
        readpv=f"{linked_pvroot}StopMode-SP",
        writepv=f"{linked_pvroot}StopMode-SP",
    ),
)

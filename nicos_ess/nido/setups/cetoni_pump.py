description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Description",
        pvroot=pump1_pvroot,
        abs_vol="pump1_vol_to_pump_absolute",
        rel_vol="pump1_vol_to_pump_relative",
    ),
    pump1_vol_to_pump_absolute=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Description",
        unit="mL",
    ),
    pump1_vol_to_pump_relative=device(
        "nicos.devices.generic.manual.ManualMove",
        description="Description",
        unit="mL",
    ),
    pump1_flowrate=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Description",
        readpv=f"{pump1_pvroot}FlowRate",
        writepv=f"{pump1_pvroot}FlowRate-SP",
    ),
    pump1_syringetype=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Description",
        readpv=f"{pump1_pvroot}SyrType-SP",
        writepv=f"{pump1_pvroot}SyrType-SP",
    ),
    pump1_stepsize=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Description",
        readpv=f"{pump1_pvroot}StepSize-SP",
        writepv=f"{pump1_pvroot}StepSize-SP",
    ),
    pump1_stepwise=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpStepper",
        description="Description",
        aspiratepv=f"{pump1_pvroot}C_AspirateStep",
        dispensepv=f"{pump1_pvroot}C_DispenseStep",
    ),
)

description = "setup for Oxford 12T recondensing magnet"

group = "plugplay"
tango_base = "tango://ccm12v:10000/box/"

includes = ["alias_T", "alias_B", "alias_sth"]

devices = dict(
    sth_ccm12v=device(
        "nicos_mlz.jcns.devices.motor.InvertableMotor",
        description="sample rotation motor",
        tangodevice=tango_base + "motor/motx",
        fmtstr="%.3f",
        precision=0.002,
    ),
    sth_ccm12v_ax=device(
        "nicos.devices.generic.Axis",
        description="sample rotation motor, with backlash correction",
        motor=f"sth_{setupname}",
        coder=f"sth_{setupname}",
        fmtstr="%.3f",
        abslimits=(-360, 360),
        precision=0.002,
        backlash=-0.5,
    ),
    T_ccm12v_vti=device(
        "nicos.devices.entangle.TemperatureController",
        description="temperature control of the VTI",
        tangodevice=tango_base + "itc/vti_ctrl",
    ),
    T_ccm12v_stick=device(
        "nicos.devices.entangle.TemperatureController",
        description="temperature control of the sample stick",
        tangodevice=tango_base + "itc/stick_ctrl",
    ),
    ccm12v_vti_heater=device(
        "nicos.devices.entangle.AnalogOutput",
        description="heater setting for VTI",
        tangodevice=tango_base + "itc/vti_heater",
    ),
    ccm12v_vti_nv=device(
        "nicos.devices.entangle.AnalogOutput",
        description="needle valve opening for VTI",
        tangodevice=tango_base + "itc/needlevalve",
    ),
    ccm12v_vti_regulation=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="automatic regulation type for VTI temperature control",
        tangodevice=tango_base + "itc/vti_regulation",
        mapping=dict(none=0, heater=1, valve=2, both=3),
    ),
    ccm12v_nv_heater=device(
        "nicos.devices.entangle.AnalogOutput",
        description="needle valve heater",
        tangodevice=tango_base + "itc/nv_heater",
    ),
    # TODO: rename to ccm12v_nv_temp (device is not essential for user)
    T_ccm12v_nv=device(
        "nicos.devices.entangle.TemperatureController",
        description="temperature at needle valve",
        tangodevice=tango_base + "itc/nv_ctrl",
    ),
    B_ccm12v=device(
        "nicos.devices.entangle.Actuator",
        description="magnetic field",
        tangodevice=tango_base + "ips/field",
        precision=0.001,
    ),
    I_ccm12v_supply=device(
        "nicos.devices.entangle.AnalogInput",
        description="actual current output of power supplies",
        tangodevice=tango_base + "ips/current",
    ),
    ccm12v_Tmag=device(
        "nicos.devices.entangle.Sensor",
        description="temperature of magnet coils",
        tangodevice=tango_base + "ips/temp",
    ),
    ccm12v_Tpt1=device(
        "nicos.devices.entangle.Sensor",
        description="temperature of pulse tube stage 1",
        tangodevice=tango_base + "ips/pt1_temp",
    ),
    ccm12v_Tpt2=device(
        "nicos.devices.entangle.Sensor",
        description="temperature of pulse tube stage 2",
        tangodevice=tango_base + "ips/pt2_temp",
    ),
    ccm12v_pdewar=device(
        "nicos.devices.entangle.TemperatureController",
        description="He pressure in dewar",
        tangodevice=tango_base + "itc/condenser_pressure",
    ),
    ccm12v_pdewar_heater=device(
        "nicos.devices.generic.paramdev.ReadonlyParamDevice",
        description="heater output (in %) for dewar heating",
        device="ccm12v_pdewar",
        parameter="heateroutput",
        unit="%",
    ),
    ccm12v_Precon=device(
        "nicos.devices.entangle.Sensor",
        description="Power applied at recondenser in Watt",
        tangodevice=tango_base + "itc/recon_pwr",
        unit="W",
    ),
    ccm12v_LHe=device(
        "nicos.devices.entangle.Sensor",
        description="liquid helium level",
        tangodevice=tango_base + "ips/level",
    ),
    ccm12v_ppump=device(
        "nicos.devices.entangle.Sensor",
        description="pressure at VTI pump",
        tangodevice=tango_base + "leybold/ch1",
    ),
    ccm12v_psamplespace=device(
        "nicos.devices.entangle.Sensor",
        description="pressure at sample space",
        tangodevice=tango_base + "leybold/ch2",
    ),
)

alias_config = {
    "T": {"T_ccm12v_vti": 220, "T_ccm12v_stick": 210},
    "Ts": {"T_ccm12v_stick": 120},
    "B": {"B_ccm12v": 100},
    "sth": {"sth_ccm12v_ax": 250, "sth_ccm12v": 200},
}

extended = dict(
    representative="B_ccm12v",
)

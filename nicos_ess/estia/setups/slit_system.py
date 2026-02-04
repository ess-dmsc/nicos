description = "The slit arrangement with 4 motors"
prefix = "ESTIA-SpSl:MC-Sl"

devices = dict(
    blade_l=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Left blade",
        motorpv=f"{prefix}Yp:Mtr",
    ),
    blade_r=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Right blade",
        motorpv=f"{prefix}Ym:Mtr",
    ),
    blade_t=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Top blade",
        motorpv=f"{prefix}Zp:Mtr",
    ),
    blade_b=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Bottom blade",
        motorpv=f"{prefix}Zm:Mtr",
    ),
    slit_1=device(
        "nicos.devices.generic.slit.Slit",
        description="Slit 1 with left, right, bottom and top motors",
        opmode="centered",
        left="blade_l",
        right="blade_r",
        top="blade_t",
        bottom="blade_b",
    ),
)

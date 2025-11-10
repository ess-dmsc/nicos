description = "The Virtual Source Slit Set"

pv_root_1 = "ESTIA-VSSlN:MC-"
pv_root_2 = "ESTIA-VSSlP:MC-"

devices = dict(
    vss_n_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Motion Negative X",
        motorpv=f"{pv_root_1}LinX-01:Mtr",
    ),
    vss_n_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Motion Negative Z",
        motorpv=f"{pv_root_1}LinZ-01:Mtr",
    ),
    vss_p_x=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Motion Positive X",
        motorpv=f"{pv_root_2}LinX-01:Mtr",
    ),
    vss_p_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Motion Positive Z",
        motorpv=f"{pv_root_2}LinZ-01:Mtr",
    ),
    vss_rot_z=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Slit Motion Rotary Z",
        motorpv="ESTIA-VSRot:MC-RotZ-01:Mtr",
    ),
    virtual_source_slit=device(
        "nicos.devices.generic.slit.Slit",
        description="Slit 1 with left, right, bottom and top motors",
        left="vss_p_x",
        right="vss_n_x",
        top="vss_p_z",
        bottom="vss_n_z",
    ),
)

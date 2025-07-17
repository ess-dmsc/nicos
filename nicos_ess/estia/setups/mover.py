description = "Selene1 mover motors"

devices = dict(
    m1_mover_fl_re_us=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M1 Selene1 1-Mover FL-RE-US",
        motorpv=f"ESTIA-SG1SM:MC-RotX-01:Mtr",
        has_powerauto=False,
    ),
    m2_mover_pr_re_ds=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M2 Selene1 1-Mover PR-RE-DS",
        motorpv=f"ESTIA-SG1SM:MC-RotX-02:Mtr",
        has_powerauto=False,
    ),
    m3_mover_pr_li_ds=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M3 Selene1 1-Mover PR-LI-DS",
        motorpv=f"ESTIA-SG1SM:MC-RotX-03:Mtr",
        has_powerauto=False,
    ),
    m4_mover_pr_li_us1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M4 Selene1 2-Mover PR-LI-US-1",
        motorpv=f"ESTIA-SG1DM:MC-RotX-01:Mtr",
        has_powerauto=False,
    ),
    m5_mover_pr_li_us2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M5 Selene1 2-Mover PR-LI-US-2",
        motorpv=f"ESTIA-SG1DM:MC-RotX-02:Mtr",
        has_powerauto=False,
    ),
)

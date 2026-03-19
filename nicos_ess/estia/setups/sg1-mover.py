description = "Selene1 mover motors"

pvprefix_1 = "ESTIA-SG1SM:MC-RotX-"
pvprefix_2 = "ESTIA-SG1DM:MC-RotX-"

devices = dict(
    m1_mover_fl_re_us_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M1 Selene1 1-Mover FL-RE-US",
        motorpv=f"{pvprefix_1}01:Mtr",
    ),
    m2_mover_pr_re_ds_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M2 Selene1 1-Mover PR-RE-DS",
        motorpv=f"{pvprefix_1}02:Mtr",
    ),
    m3_mover_pr_li_ds_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M3 Selene1 1-Mover PR-LI-DS",
        motorpv=f"{pvprefix_1}03:Mtr",
    ),
    m4_mover_pr_li_us1_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M4 Selene1 2-Mover PR-LI-US-1",
        motorpv=f"{pvprefix_2}01:Mtr",
    ),
    m5_mover_pr_li_us2_1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M5 Selene1 2-Mover PR-LI-US-2",
        motorpv=f"{pvprefix_2}02:Mtr",
    ),
    mover=device(
        "nicos_ess.estia.devices.mover.SeleneMover",
        description="Selene1 1-Mover",
        s1="m1_mover_fl_re_us_1",
        s2="m2_mover_pr_re_ds_1",
        s3="m3_mover_pr_li_ds_1",
        s4="m4_mover_pr_li_us1_1",
        s5="m5_mover_pr_li_us2_1",
        mover_length=2750,
        beam_height=1088,
    ),
)

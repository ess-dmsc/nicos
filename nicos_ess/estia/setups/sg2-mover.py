description = "Selene2 mover motors"

pvprefix_1 = "ESTIA-SG2SM:MC-RotX-"
pvprefix_2 = "ESTIA-SG2DM:MC-RotX-"

devices = dict(
    m1_mover_fl_re_us_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M1 Selene2 1-Mover FL-RE-US",
        motorpv=f"{pvprefix_1}01:Mtr",
        visibility=(),
    ),
    m2_mover_pr_re_ds_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M2 Selene2 1-Mover PR-RE-DS",
        motorpv=f"{pvprefix_1}02:Mtr",
        visibility=(),
    ),
    m3_mover_pr_li_ds_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M3 Selene2 1-Mover RP-LI-DS",
        motorpv=f"{pvprefix_1}03:Mtr",
        visibility=(),
    ),
    m4_mover_pr_li_us1_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M4 Selene2 2-Mover PR-LI-US-1",
        motorpv=f"{pvprefix_2}01:Mtr",
        visibility=(),
    ),
    m5_mover_pr_li_us2_2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M5 Selene2 2-Mover PR-Li-US-2",
        motorpv=f"{pvprefix_2}02:Mtr",
        visibility=(),
    ),
    m6_horizontal_mover=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M5 Selene2 Horizontal Mover",
        motorpv="ESTIA-SG2Mv:MC-LinX-01:Mtr",
        visibility=(),
    ),
    mover2=device(
        "nicos_ess.estia.devices.mover.SeleneMover",
        description="Selene2 1-Mover",
        s1="m1_mover_fl_re_us_2",
        s2="m2_mover_pr_re_ds_2",
        s3="m3_mover_pr_li_ds_2",
        s4="m4_mover_pr_li_us1_2",
        s5="m5_mover_pr_li_us2_2",
        mover_length=3600,
        beam_height=1098,
        visibility=(),
    ),
)

description = "Selene2 mover motors"

pvprefix_1 = "ESTIA-SG2SM:MC-RotX-"
pvprefix_2 = "ESTIA-SG2DM:MC-RotX-"

devices = dict(
    m1_mover_fl_re_us=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M1 Selene2 1-Mover FL-RE-US",
        motorpv=f"{pvprefix_1}01:Mtr",
        abslimits=(90, 270),
        unit="deg",
        speed=0.2,
    ),
    m2_mover_pr_re_ds=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M2 Selene2 1-Mover PR-RE-DS",
        motorpv=f"{pvprefix_1}02:Mtr",
        abslimits=(90, 270),
        unit="deg",
        speed=0.2,
    ),
    m3_mover_pr_li_ds=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M3 Selene2 1-Mover RP-LI-DS",
        motorpv=f"{pvprefix_1}03:Mtr",
        abslimits=(90, 270),
        unit="deg",
        speed=0.2,
    ),
    m4_mover_pr_li_us1=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M4 Selene2 2-Mover PR-LI-US-1",
        motorpv=f"{pvprefix_2}01:Mtr",
        abslimits=(90, 270),
        unit="deg",
        speed=0.2,
    ),
    m5_mover_pr_li_us2=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="M5 Selene2 2-Mover PR-Li-US-2",
        motorpv=f"{pvprefix_2}02:Mtr",
        abslimits=(90, 270),
        unit="deg",
        speed=0.2,
    ),
)

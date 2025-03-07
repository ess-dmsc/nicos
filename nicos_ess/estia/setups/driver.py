description = "Motors for Driver1"

pvprefix = "PSI-ESTIARND:MC-MCU-01:"

devices = dict(
    driver1_1_approach=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Mtr8 Driver1-1 Approach",
        motorpv=f"{pvprefix}Mtr8",
        unit="mm",
        abslimits=(0, 25),
        userlimits=(0, 25),
    ),
    driver1_1_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Mtr10 Driver1-1 Adjust",
        motorpv=f"{pvprefix}Mtr10",
        unit="mm",
        abslimits=(0, 360),
        userlimits=(0, 360),
    ),
    driver1_1_hex_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Hexscrew state",
        readpv=f"{pvprefix}Mtr8-HexScrew",
    ),
    driver1_2_approach=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Mtr9 Driver1-2 Approach",
        motorpv=f"{pvprefix}Mtr9",
        unit="mm",
        abslimits=(0, 25),
        userlimits=(0, 25),
    ),
    driver1_2_adjust=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Mtr11 Driver1-2 Adjust",
        motorpv=f"{pvprefix}Mtr11",
        unit="mm",
        abslimits=(0, 360),
        userlimits=(0, 360),
    ),
    driver1_2_hex_state=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Hexscrew state",
        readpv=f"{pvprefix}Mtr9-HexScrew",
    ),
)

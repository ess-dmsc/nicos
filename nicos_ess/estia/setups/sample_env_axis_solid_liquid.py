description = (
    "Sample Environment Axis for The Solid Liquid Sample Changer."
    "Same axis as the Room Temperature Sample Changer but with "
    "different mapping"
)

devices = dict(
    solid_liquid_motor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample Environment Axis",
        motorpv="ESTIA-SpSt:MC-LinY-01:Mtr",
        visibility=(),
    ),
    solid_liquid_macro=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Preset controls for sampe axis",
        controlled_device="solid_liquid_motor",
        mapping={"Base": 1},
    ),
)

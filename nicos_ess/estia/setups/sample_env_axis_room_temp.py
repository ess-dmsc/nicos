description = (
    "Sample Environment Axis for The Room Temperature Sample Changer."
    "Same axis as the Solid Liquid Sample Changer but with "
    "different mapping"
)

devices = dict(
    room_temp_mover=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Sample Environment Axis",
        motorpv="ESTIA-SpSt:MC-LinY-01:Mtr",
        visibility=(),
    ),
    room_temp_macro=device(
        "nicos_ess.devices.mapped_controller.MappedController",
        description="Preset controls for sample axis",
        controlled_device="room_temp_mover",
        mapping={"Base": 1},
    ),
)

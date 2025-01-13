description = "The motor for controlling the camera position"

devices = dict(
    camera_box_motor=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="The camera box motor",
        motorpv="YMIR-4004:MC-MCU-02:Mtr4",
    ),
    brake=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The brake for the camera box motor",
        readpv="YMIR-4004:MC-MCU-02:Mtr4-ReleaseBrake",
        writepv="YMIR-4004:MC-MCU-02:Mtr4-ReleaseBrake",
    ),
)

description = "TBL adjustable collimator set"

collimator_map={
    "LNN": (144.14, 65, 80),
    "LN1": (144.14, 65, 35),
    "LN3": (144.14, 65, 0),
    "LSN": (144.14, 6, 80),
    "LS1": (144.14, 6, 35),
    "LS3": (144.14, 6, 0),
    "3N1": (74.14, 100, 104.8),
    "3N3": (74.14, 100, 69.8),
    "3N5": (74.14, 100, 34.8),
    "3N10": (74.14, 100, 0),
    "3S1": (74.14, 76, 104.8),
    "3S3": (74.14, 76, 69.8),
    "3S5": (74.14, 76, 34.8),
    "3S10": (74.14, 76, 0),
    "3M1": (74.14, 36, 104.8),
    "3M3": (74.14, 36, 69.8),
    "3M5": (74.14,36, 34.8),
    "3M10": (74.14, 36, 0),
    "3L1": (74.14, 3, 104.8),
    "3L3": (74.14, 3, 69.8),
    "3L5": (74.14, 3, 34.8),
    "3L10": (74.14, 3, 0),
    "10M5": (4.14, 103,  105.1),
    "10M1": (4.14, 103,  70.1),
    "10MN": (4.14, 103,  0),
    "10L5": (4.14, 66, 105.1),
    "10L1": (4.14, 66, 70.1),
    "10LN": (4.14, 66, 0),
    "10N5": (4.14, 0, 105.1),
    "10N1": (4.14, 0, 70.1),
    "10NN": (4.14, 0, 0)
}

devices = dict(
    axis_attenuator_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Attenuator changer",
        motorpv="TBL-AttChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis_horizontal=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimator horizontal",
        motorpv="TBL-PinLin:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis_vertical=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Collimator horizontal",
        motorpv="TBL-PinLif:MC-LinZ-01:Mtr",
        monitor_deadband=0.01,
    ),
    axis_pinhole_changer=device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description="Pinhole changer",
        motorpv="TBL-PinChg:MC-LinY-01:Mtr",
        monitor_deadband=0.01,
    ),
    config_set=device(
        "nicos_ess.devices.mapped_controller.MultiTargetMapping",
        controlled_devices=[
            "axis_horizontal",
            "axis_attenuator_changer",
            "axis_pinhole_changer"
        ],
        mapping=collimator_map
    ),
    multi_target_composer=device(
        "nicos_ess.devices.mapped_controller.MultiTargetComposer",
        unit="",
        composition_output="config_set",
        composition_inputs=[
            "config_collimator",
            "config_attenuator",
            "config_pinhole"
        ],
        visibility=()
    ),
    config_collimator=device(
        "nicos_ess.devices.mapped_controller.MultiTargetSelector",
        controlled_device="multi_target_composer",
        default="L",
        mapping={
            "Large collimator": "L",
            "3 mm collimator": "3",
            "10 mm collimator": "10",
        }
    ),
    config_attenuator=device(
        "nicos_ess.devices.mapped_controller.MultiTargetSelector",
        controlled_device="multi_target_composer",
        default="N",
        mapping={
            "No attenuator": "N",
            "Small attenuator": "S",
            "Medium attenuator": "M",
            "Large attenuator": "L",
        }
    ),
    config_pinhole=device(
        "nicos_ess.devices.mapped_controller.MultiTargetSelector",
        controlled_device="multi_target_composer",
        default="1",
        mapping={
            "No pinhole": "N",
            "1 mm pinhole": "1",
            "3 mm pinhole": "3",
            "5 mm pinhole": "5",
            "10 mm pinhole": "10",
        }
    ),
)
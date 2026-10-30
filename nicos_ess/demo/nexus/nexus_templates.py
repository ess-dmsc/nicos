from nicos_ess.nexus import DeviceDataset, EventStream

demo_default = {
    "NeXus_Version": "4.3.0",
    "instrument": "DEMO",
    "entry1:NXentry": {
        "comment": DeviceDataset("Exp", "remark"),
        "title": DeviceDataset("Exp", "title"),
        "experiment_identifier": DeviceDataset("Exp", "proposal"),
        "user:NXuser": {
            "name": DeviceDataset("Exp", "users"),
        },
        "motion:NXentry": {
            "motor": EventStream(
                "Demo_motion",
                "SES-SCAN:MC-MCU-001:m1.RBV",
                mod="f142",
                dtype="double",
            ),
        },
    },
}

description = "Slits S1 virtual axes"
slits_set_name = "slits_S1"
motorpv_prefix = "TBL-"
virtual_axes = [
    {
        "name": "horizontal_center",
        "description": "Slits S1 Horizontal Center",
        "motorpv_suffix": "Sl1:MC-Yc-01",
    },
    {
        "name": "horizontal_gap",
        "description": "Slits S1 Horizontal Gap",
        "motorpv_suffix": "Sl1:MC-Yg-01",
    },
    {
        "name": "vertical_center",
        "description": "Slits S1 Vertical Center",
        "motorpv_suffix": "Sl1:MC-Zc-01",
    },
    {
        "name": "vertical_gap",
        "description": "Slits S1 Vertical Gap",
        "motorpv_suffix": "Sl1:MC-Zg-01",
    },
]

for virtual_axis in virtual_axes:
    devices[f"{slits_set_name}_{virtual_axis["name"]}"] = device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description=f"{virtual_axis["description"]}",
        motorpv=f"{motorpv_prefix}{virtual_axis["motorpv_suffix"]}",
        monitor_deadband=0.01,
    )
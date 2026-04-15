description = "Slits 2 virtual axes"
slits_set_name = "slits_2"
motorpv_prefix = "TBL-"
virtual_axes = [
    {
        "name": "horizontal_center",
        "description": "Slits 2 Horizontal Center",
        "motorpv_suffix": "Sl2:MC-Yc-01",
    },
    {
        "name": "horizontal_gap",
        "description": "Slits 2 Horizontal Gap",
        "motorpv_suffix": "Sl2:MC-Yg-01",
    },
    {
        "name": "vertical_center",
        "description": "Slits 2 Vertical Center",
        "motorpv_suffix": "Sl2:MC-Zc-01",
    },
    {
        "name": "vertical_gap",
        "description": "Slits 2 Vertical Gap",
        "motorpv_suffix": "Sl2:MC-Zg-01",
    },
]

for virtual_axis in virtual_axes:
    devices[f"{slits_set_name}_{virtual_axis["name"]}"] = device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description=f"{virtual_axis["description"]}",
        motorpv=f"{motorpv_prefix}{virtual_axis["motorpv_suffix"]}",
        monitor_deadband=0.01,
    )
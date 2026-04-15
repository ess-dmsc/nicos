description = "Slits L virtual axes"
slits_set_name = "slits_L"
motorpv_prefix = "TBL-"
virtual_axes = [
    {
        "name": "horizontal_center",
        "description": "Slits L Horizontal Center",
        "motorpv_suffix": "SlL:MC-Yc-01",
    },
    {
        "name": "horizontal_gap",
        "description": "Slits L Horizontal Gap",
        "motorpv_suffix": "SlL:MC-Yg-01",
    },
    {
        "name": "vertical_center",
        "description": "Slits L Vertical Center",
        "motorpv_suffix": "SlL:MC-Zc-01",
    },
    {
        "name": "vertical_gap",
        "description": "Slits L Vertical Gap",
        "motorpv_suffix": "SlL:MC-Zg-01",
    },
]

for virtual_axis in virtual_axes:
    devices[f"{slits_set_name}_{virtual_axis["name"]}"] = device(
        "nicos_ess.devices.epics.pva.motor.EpicsMotor",
        description=f"{virtual_axis["description"]}",
        motorpv=f"{motorpv_prefix}{virtual_axis["motorpv_suffix"]}",
        monitor_deadband=0.01,
    )
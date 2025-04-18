description = "Emulation of the hardware chopper"

group = "lowlevel"

devices = dict(
    software=device(
        "nicos.devices.generic.ManualSwitch",
        description="Software of chopper",
        states=["Manual"],
        fmtstr="%s",
    ),
    chopper_disk1=device(
        "nicos.devices.generic.ManualMove",
        description="MC chopper_disk1",
        abslimits=(0, 6000),
        fmtstr="%d",
        unit="rpm",
    ),
    chopper_disk2=device(
        "nicos.devices.generic.ManualMove",
        description="MC chopper_disk2",
        abslimits=(-180, 360),
        fmtstr="%.2f",
        unit="Grad",
    ),
    chopper_disk3=device(
        "nicos.devices.generic.ManualMove",
        description="MC chopper_disk3",
        abslimits=(-180, 360),
        fmtstr="%.2f",
        unit="Grad",
    ),
    chopper_disk4=device(
        "nicos.devices.generic.ManualMove",
        description="MC chopper_disk4",
        abslimits=(-180, 360),
        fmtstr="%.2f",
        unit="Grad",
    ),
    chopper_disk5=device(
        "nicos.devices.generic.ManualMove",
        description="sc2 chopper_disk5 gear=2",
        abslimits=(-180, 360),
        fmtstr="%.2f",
        unit="Grad",
    ),
    chopper_disk6=device(
        "nicos.devices.generic.ManualMove",
        description="sc2 chopper_disk6 gear=2",
        abslimits=(-180, 360),
        fmtstr="%.2f",
        unit="Grad",
    ),
    disc2_pos=device(
        "nicos.devices.generic.ManualSwitch",
        description="pos of disk2",
        states=[i for i in range(1, 5 + 1)],
        fmtstr="%d",
        unit="",
    ),
)

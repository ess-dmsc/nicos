name = "calculation devices"

includes = ["generic"]

devices = dict(
    cdev1=device(
        "nicos.devices.generic.VirtualMotor",
        curvalue=1,
        unit="mm",
        abslimits=(1, 1),
    ),
    cdev2=device(
        "nicos.devices.generic.VirtualMotor",
        curvalue=2,
        unit="mm",
        abslimits=(2, 2),
    ),
    sumdev=device(
        "nicos.devices.generic.CalculatedReadable",
        op="+",
        device1="cdev1",
        device2="cdev2",
    ),
    diffdev=device(
        "nicos.devices.generic.CalculatedReadable",
        op="-",
        device1="cdev1",
        device2="cdev2",
    ),
    muldev=device(
        "nicos.devices.generic.CalculatedReadable",
        op="*",
        device1="cdev1",
        device2="cdev2",
    ),
    divdev=device(
        "nicos.devices.generic.CalculatedReadable",
        op="/",
        device1="cdev1",
        device2="cdev2",
    ),
    sumdevfail=device(
        "nicos.devices.generic.CalculatedReadable",
        op="add",
        device1="cdev1",
        device2=device(
            "nicos.devices.generic.VirtualMotor",
            curvalue=0.002,
            abslimits=(0.002, 0.002),
            unit="m",
        ),
    ),
)

description = "Non-electronically adjustable parameters of the detector"

group = "optional"

devices = dict(
    scintillator=device(
        "nicos.devices.generic.manual.ManualSwitch",
        description="Scintillator installed in the camera box",
        states=[
            "050um LiF:ZnS",
            "100um LiF:ZnS",
            "150um LiF:ZnS",
            "200um LiF:ZnS",
            "300um LiF:ZnS",
            "010um Gd2O2S",
            "020um Gd2O2S",
            "other",
        ],
    ),
    lens=device(
        "nicos.devices.generic.manual.ManualSwitch",
        description="Lens installed in the camera box",
        states=[
            "Leica 100mm F2.8",
            "Leica 100mm with macro adapter",
            "Zeiss 100mm F2.0",
            "other",
        ],
    ),
    pixelsize=device(
        "nicos.devices.generic.manual.ManualMove",
        description="effective pixel size on the scintillator",
        abslimits=(0, 1e6),
        unit="um",
        fmtstr="%.2f",
    ),
    camerabox=device(
        "nicos.devices.generic.manual.ManualSwitch",
        description="Used camera box",
        states=[
            "Black Box",
            "Neo Box 2019 - 1 mirror config 1:1",
            "Neo Box 2019 - 2 mirror config 1:4",
            "Neo Box 2019 - 2 mirror config 1:8",
            "Large detector in chamber 2",
            "other",
        ],
    ),
)

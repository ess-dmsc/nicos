includes = ["stdsystem"]

devices = dict(
    capillary_selector=device(
        "nicos_tuw.xccm.devices.capillary_selector.CapillarySelector",
        moveables=["cap_Ty", "cap_Tz"],
        fallback=0,
        fmtstr="%d",
        mapping={
            1: [0, 10],
            2: [10, 10],
            3: [5, 0],
        },
        precision=[0.1, 0.1],
    ),
    cap_Ty_m=device(
        "nicos.devices.generic.VirtualMotor",
        fmtstr="%.2f",
        abslimits=(0, 10),
        visibility=(),
        unit="mm",
    ),
    cap_Ty=device(
        "nicos.devices.generic.Axis",
        motor="cap_Ty_m",
        precision=1.0,
    ),
    cap_Tz_m=device(
        "nicos.devices.generic.VirtualMotor",
        fmtstr="%.2f",
        abslimits=(0, 10),
        visibility=(),
        unit="mm",
    ),
    cap_Tz=device(
        "nicos.devices.generic.Axis",
        motor="cap_Tz_m",
        precision=1.0,
    ),
    det=device(
        "nicos.devices.generic.Detector",
        description="Detector",
        timers=[
            device(
                "nicos_tuw.xccm.devices.detector.Timer",
                digitalio=device(
                    "nicos.devices.generic.ManualSwitch",
                    states=[0, 1],
                    fmtstr="%d",
                ),
            ),
        ],
    ),
    opt_Tx_m=device(
        "nicos.devices.generic.VirtualMotor",
        fmtstr="%.2f",
        abslimits=(0, 99),
        visibility=(),
        unit="mm",
    ),
    opt_Tx=device(
        "nicos.devices.generic.Axis",
        motor="opt_Tx_m",
        precision=0.01,
    ),
    opt_Ty_m=device(
        "nicos.devices.generic.VirtualMotor",
        fmtstr="%.2f",
        abslimits=(0, 100),
        visibility=(),
        unit="mm",
    ),
    opt_Ty=device(
        "nicos.devices.generic.Axis",
        motor="opt_Ty_m",
        precision=0.01,
    ),
    opt_Rz_m=device(
        "nicos.devices.generic.VirtualMotor",
        description="Optics rotation z-Axis motor",
        fmtstr="%.2f",
        abslimits=(-180, 180),  # in real config limits are -360,360 maybe a bit much
        visibility=(),
        unit="degrees",
    ),
    opt_Rz=device(
        "nicos.devices.generic.Axis",
        description="Optics rotation z-axis",
        motor="opt_Rz_m",
        precision=0.01,
    ),
    optic_tool_switch=device(
        "nicos_tuw.xccm.devices.optic_tool_switch.OpticToolSwitch",
        description="change the position of the optics from between beam and sample to between sample and detector (or vice versa)",
        moveables=["opt_Tx", "opt_Ty", "opt_Rz"],
        mapping={
            1: [10, 10, 0],
            2: [40, 60, 90],
            3: [90, 10, 0],
        },
        precision=[10, 10, 30],
    ),
)

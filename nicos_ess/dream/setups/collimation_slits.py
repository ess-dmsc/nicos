description = "Collimation slits"

blades = {
    "left": "Yp",
    "right": "Ym",
    "lower": "Zm",
    "upper": "Zp",
}

devices=dict()

for slit_set in range(1,4):
    for blade in blades:
        devices[f"slit_set_{slit_set}_{blade}"] = device(
            "nicos_ess.devices.epics.pva.motor.SmaractPiezoMotor",
            description=f"Sample slit set {slit_set}, {blade} blade",
            motorpv=f"DREAM-ColSl{slit_set}:MC-Sl{blades[blade]}-01:PzMtr",
            has_powerauto=False,
            has_msgtxt=False,
            has_errorbit=False,
            has_reseterror=False,
            monitor_deadband=0.01,
        )

    devices[f"slit_set_{slit_set}"] = device(
        "nicos.devices.generic.slit.Slit",
        description=f"Slit {slit_set} with left, right, bottom and top motors",
        opmode="centered",
        left=f"slit_set_{slit_set}_left",
        right=f"slit_set_{slit_set}_right",
        top=f"slit_set_{slit_set}_upper",
        bottom=f"slit_set_{slit_set}_lower",
    )

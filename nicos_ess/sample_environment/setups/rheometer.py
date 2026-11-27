description = "Anton-Paar MCR 702e rheometer"

group = "plugplay"

pv_root = "SE-SEE:SE-RHEO-001:"

extended = dict(
    presence_signal=f"pva://{pv_root}DeviceTemp-R",
)

devices = dict(
    rheometer=device(
        "nicos_ess.devices.epics.ap_rheometer.RheometerControl",
        description="Anton-Paar MCR 702e rheometer (interval config + measurement)",
        pv_root=pv_root,
    ),
)

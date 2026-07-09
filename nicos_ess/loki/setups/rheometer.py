description = "Anton-Paar MCR 702e rheometer"

pv_root = "SE-SEE:SE-RHEO-001:"

devices = dict(
    rheometer=device(
        "nicos_ess.devices.epics.ap_rheometer.RheometerControl",
        description="Anton-Paar MCR 702e rheometer (interval config + measurement)",
        pv_root=pv_root,
    ),
)

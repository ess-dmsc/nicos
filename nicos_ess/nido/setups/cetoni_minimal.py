description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"
pump2_pvroot = "B02-CSLab:SE-Pumps:SP2"
linked_pvroot = "B02-CSLab:SE-Pumps:Lnk"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_minimal.CetoniPumpController",
        description="Description",
        pvroot=pump1_pvroot,
    ),
    pump1_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        readpv=f"{pump1_pvroot}SyrType-SP",
        writepv=f"{pump1_pvroot}SyrType-SP",
    ),
    pump2=device(
        "nicos_ess.loki.devices.cetoni_minimal.CetoniPumpController",
        description="Description",
        pvroot=pump2_pvroot,
    ),
    pump2_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        readpv=f"{pump2_pvroot}SyrType-SP",
        writepv=f"{pump2_pvroot}SyrType-SP",
    ),
    pump_linked_mode=device(
        "nicos_ess.loki.devices.cetoni_minimal.CetoniPumpLinkedMode",
        pvroot="",
    ),
)

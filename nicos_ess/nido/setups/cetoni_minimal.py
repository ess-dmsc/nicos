description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"
pump2_pvroot = "B02-CSLab:SE-Pumps:SP2"

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
)

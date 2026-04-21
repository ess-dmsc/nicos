description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_minimal.CetoniPumpController",
        description="Description",
        pvroot=pump1_pvroot,
        syringe_config="pump1_syringe_config",
    ),
    pump1_syringe_config=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        readpv=f"{pump1_pvroot}SyrType-SP",
        writepv=f"{pump1_pvroot}SyrType-SP",
    ),
)

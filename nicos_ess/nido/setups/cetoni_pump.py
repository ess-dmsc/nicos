description = "The cetoni pumps"

pump1_pvroot = "B02-CSLab:SE-Pumps:SP1"

devices = dict(
    pump1=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Description",
        pvroot=pump1_pvroot,
    ),
    pump1_syringe_type=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Description",
        readpv=f"{pump1_pvroot}SyrType-SP",
        writepv=f"{pump1_pvroot}SyrType-SP",
    ),
)

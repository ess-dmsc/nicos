description = "The cetoni pumps"

devices = dict(
    pump_1=device(
        "nicos_ess.loki.devices.cetoni_pump.CetoniPumpController",
        description="Description",
        pvroot="B02-CSLab:SE-Pumps:SP1",
        fmtstr="%.3f",
    ),
)

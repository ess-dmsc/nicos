description = "Outside world data"
group = "lowlevel"

devices = dict(
    meteo=device(
        "nicos.devices.entangle.Sensor",
        description="Outdoor air temperature",
        tangodevice="tango://ictrlfs.ictrl.frm2.tum.de:10000/frm2/meteo/temp",
    ),
)

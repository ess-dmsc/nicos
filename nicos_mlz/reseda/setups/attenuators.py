description = "Attenuators"
group = "optional"
display_order = 2
tango_base = "tango://resedahw2.reseda.frm2.tum.de:10000/reseda/iobox"

devices = dict(
    att0=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Attenuator 0: factor 3",
        tangodevice="%s/plc_spare_out_6" % tango_base,
        mapping={"in": 1, "out": 0},
        unit="",
        maxage=119,
        pollinterval=60,
    ),
    att1=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Attenuator 1: factor 15",
        tangodevice="%s/plc_spare_out_7" % tango_base,
        mapping={"in": 1, "out": 0},
        unit="",
        maxage=119,
        pollinterval=60,
    ),
    att2=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Attenuator 2: factor 30",
        tangodevice="%s/plc_spare_out_8" % tango_base,
        mapping={"in": 1, "out": 0},
        unit="",
        maxage=119,
        pollinterval=60,
    ),
)

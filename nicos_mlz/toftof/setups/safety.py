description = "safety system and shutter"

group = "lowlevel"

tango_base = "tango://tofhw.toftof.frm2.tum.de:10000/toftof/"

devices = dict(
    saf=device(
        "nicos_mlz.toftof.devices.SafetyInputs",
        description="State of the safety control",
        i7053=["i7053_1", "i7053_2", "i7053_3"],
        fmtstr="0x%012x",
    ),
    i7053_1=device(
        "nicos.devices.entangle.DigitalInput",
        visibility=(),
        tangodevice=tango_base + "sec/70531",
        fmtstr="0x%04x",
    ),
    i7053_2=device(
        "nicos.devices.entangle.DigitalInput",
        visibility=(),
        tangodevice=tango_base + "sec/70532",
        fmtstr="0x%04x",
    ),
    i7053_3=device(
        "nicos.devices.entangle.DigitalInput",
        visibility=(),
        tangodevice=tango_base + "sec/70533",
        fmtstr="0x%04x",
    ),
    shopen=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "shutter/open",
        visibility=(),
    ),
    shclose=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "shutter/close",
        visibility=(),
    ),
    shstatus=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "shutter/status",
        visibility=(),
    ),
    shutter=device(
        "nicos_mlz.toftof.devices.Shutter",
        description="Instrument shutter",
        open="shopen",
        close="shclose",
        status="shstatus",
        unit="",
    ),
)

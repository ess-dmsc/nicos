description = "base setup for all instrument configurations"
group = "lowlevel"

# CASCADE gasmix setup always included!
includes = ["system", "slits", "guidehall", "nl6", "reactor", "gas"]

tango_base = "tango://miractrl.mira.frm2.tum.de:10000/mira/"

devices = dict(
    atten1_v=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch6",
        mapping={"out": 0, "in": 1},
        visibility=(),
        warnlimits=("out", "out"),
    ),
    atten1_i=device(
        "nicos_mlz.mira.devices.beckhoff.DigitalInput",
        tangodevice=tango_base + "beckhoff/beckhoff2",
        offset=1,
        visibility=(),
    ),
    atten1_o=device(
        "nicos_mlz.mira.devices.beckhoff.DigitalInput",
        tangodevice=tango_base + "beckhoff/beckhoff2",
        offset=0,
        visibility=(),
    ),
    atten1=device(
        "nicos_mlz.mira.devices.switches.BeamElement",
        description="attenuator 1 (factor 6 at 4.5 Ang) in the beam?",
        valve="atten1_v",
        switch_in="atten1_i",
        switch_out="atten1_o",
        warnlimits=("out", "out"),
    ),
    atten2_v=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch7",
        mapping={"out": 0, "in": 1},
        visibility=(),
    ),
    atten2_i=device(
        "nicos_mlz.mira.devices.beckhoff.DigitalInput",
        tangodevice=tango_base + "beckhoff/beckhoff2",
        offset=3,
        visibility=(),
    ),
    atten2_o=device(
        "nicos_mlz.mira.devices.beckhoff.DigitalInput",
        tangodevice=tango_base + "beckhoff/beckhoff2",
        offset=2,
        visibility=(),
    ),
    atten2=device(
        "nicos_mlz.mira.devices.switches.BeamElement",
        description="attenuator 2 (factor 36 at 4.5 Ang) in the beam?",
        valve="atten2_v",
        switch_in="atten2_i",
        switch_out="atten2_o",
        warnlimits=("out", "out"),
    ),
    lamfilter=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch4",
        mapping={"in": 0, "out": 1},
        description="beryllium filter in the beam?",
        warnlimits=("in", "in"),
    ),
    FOL=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch0",
        mapping={"out": 0, "in": 1},
        description="frame overlap mirror in the beam?",
        visibility=(),  # not used currently
    ),
    flip1=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch1",
        mapping={"out": 0, "in": 1},
        description="flipper in MIRA-1 shielding in the beam?",
        visibility=(),  # not used currently
    ),
    flip2=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch3",
        mapping={"in": 0, "out": 1},
        description="flipper and guide field in MIRA-2 shielding table in the beam?",
    ),
    ms2pos=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        tangodevice=tango_base + "valve/ch5",
        mapping={"out": 0, "in": 1},
        description="slit after MIRA-2 shielding exit in the beam?",
        warnlimits=("in", "in"),
    ),
    Shutter=device(
        "nicos_mlz.mira.devices.shutter.Shutter",
        description="MIRA shutter position",
        tangodevice=tango_base + "beckhoff/beckhoff2",
        openoffset=8,
        closeoffset=9,
        switchoffset=0,
        warnlimits=("open", "open"),
        unit="",
    ),
    PSDGas=device(
        "nicos_mlz.mira.devices.beckhoff.NamedDigitalInput",
        description="sensor to indicate low pressure in CO2 gas of CASCADE",
        mapping={"empty": 0, "okay": 1},
        warnlimits=("okay", "okay"),
        pollinterval=10,
        maxage=30,
        tangodevice=tango_base + "beckhoff/beckhoff2",
        offset=6,
    ),
    Cooling=device(
        "nicos_mlz.mira.devices.beckhoff.NamedDigitalInput",
        description="sensor for MIRA cooling water filling level",
        mapping={"refill": 0, "okay": 1},
        warnlimits=("okay", "okay"),
        pollinterval=10,
        maxage=30,
        tangodevice=tango_base + "beckhoff/beckhoff2",
        offset=7,
    ),
    CoolTemp=device(
        "nicos.devices.entangle.AnalogInput",
        description="temperature of MIRA cooling water",
        tangodevice=tango_base + "i7000/cooltemp",
        warnlimits=(10, 25),
        pollinterval=10,
        maxage=30,
        fmtstr="%.1f",
    ),
)

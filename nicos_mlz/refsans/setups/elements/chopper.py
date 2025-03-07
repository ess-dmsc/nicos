description = "Chopper devices"

group = "lowlevel"

instrument_values = configdata("instrument.values")

tango_host = instrument_values["tango_base"] + "test/chopper/io"
code_base_chopper = instrument_values["code_base"] + "chopper.real."
code_base_analog = instrument_values["code_base"] + "analogencoder.AnalogEncoder"

includes = ["shutter", "vsd"]

devices = dict(
    chopper_io=device(
        "nicos.devices.entangle.StringIO",
        tangodevice=tango_host,
        visibility=(),
    ),
    chopper=device(
        code_base_chopper + "ChopperMaster",
        description="Interface",
        fmtstr="%s",
        unit="foo",
        chopper1="chopper_speed",
        chopper2="chopper2",
        chopper3="chopper3",
        chopper4="chopper4",
        chopper5="chopper5",
        chopper6="chopper6",
        shutter="shutter",
        comm="chopper_io",
    ),
    chopper_speed=device(
        code_base_chopper + "ChopperDisc",
        description="chopper speed; reguler 100rpm/min Nothalt 400rpm/min",
        comm="chopper_io",
        fmtstr="%d",
        unit="rpm",
        chopper=1,
        gear=0,
        edge="open",
    ),
    chopper2=device(
        code_base_chopper + "ChopperDisc2",
        description="disk2",
        comm="chopper_io",
        translation="chopper2_pos",
        fmtstr="%d",
        visibility=(),
        unit="rpm",
        chopper=2,
        gear=1,
        edge="close",
        reference=-18.05,
    ),
    chopper2_pos=device(
        code_base_chopper + "ChopperDiscTranslation",
        description="position of chopper disc 2",
        comm="chopper_io",
        disc="chopper2",  # because of speed
    ),
    chopper2_pos_x=device(
        code_base_chopper + "ChopperDiscTranslationEncoder",
        description="position of chopper disc 2",
        comm="chopper_io",
        unit="",
        addr=7,
        visibility=(),
    ),
    chopper2_pos_y=device(
        code_base_chopper + "ChopperDiscTranslationEncoder",
        description="position of chopper disc 2",
        comm="chopper_io",
        unit="",
        addr=8,
        visibility=(),
    ),
    chopper3=device(
        code_base_chopper + "ChopperDisc",
        description="chopper3",
        comm="chopper_io",
        fmtstr="%d",
        visibility=(),
        unit="rpm",
        chopper=3,
        gear=1,
        edge="open",
        reference=23.85,
    ),
    chopper4=device(
        code_base_chopper + "ChopperDisc",
        description="chopper4",
        comm="chopper_io",
        fmtstr="%d",
        visibility=(),
        unit="rpm",
        chopper=4,
        gear=1,
        edge="close",
        reference=29.2,
    ),
    chopper5=device(
        code_base_chopper + "ChopperDisc",
        description="chopper5",
        comm="chopper_io",
        fmtstr="%d",
        visibility=(),
        unit="rpm",
        chopper=5,
        gear=2,
        edge="open",
        reference=220.19,
    ),
    chopper6=device(
        code_base_chopper + "ChopperDisc",
        description="chopper6",
        comm="chopper_io",
        fmtstr="%d",
        unit="rpm",
        visibility=(),
        chopper=6,
        gear=2,
        edge="close",
        reference=129.7,  # 2021-04-23 07:06:24 Encoder homeRun 129.7,
    ),
    core1=device(
        code_base_analog,
        description="Temperature of motorcoil 1",
        device="Temperature8",
        poly=[-6.8, 1],  # 2020-04-07 06:27:08 -6.9
        unit="degC",
        visibility=(),
    ),
    core2=device(
        code_base_analog,
        description="Temperature of motorcoil 2",
        device="Temperature7",
        poly=[-9.3, 1],  # 2020-04-07 06:27:08 as ref
        unit="degC",
        visibility=(),
    ),
    core3=device(
        code_base_analog,
        description="Temperature of motorcoil 3",
        device="Temperature6",
        poly=[-11.0, 1],  # 2020-04-07 06:27:08 -10.1
        unit="degC",
        visibility=(),
    ),
    core4=device(
        code_base_analog,
        description="Temperature of motorcoil 4",
        device="Temperature5",
        poly=[-10.1, 1],  # 2020-04-07 06:27:08 -9.7
        unit="degC",
        visibility=(),
    ),
    core5=device(
        code_base_analog,
        description="Temperature of motorcoil 5",
        device="Temperature1",
        poly=[-10, 1],  # 2021-04-13 07:26:25 QAD
        unit="degC",
        visibility=(),
    ),
    core6=device(
        code_base_analog,
        description="Temperature of motorcoil 6",
        device="Temperature3",
        poly=[-10, 1],  # 2021-04-13 07:26:25 QAD
        unit="degC",
        visibility=(),
    ),
)

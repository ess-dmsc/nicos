description = "neutronguide"

group = "lowlevel"

includes = ["nok_ref", "zz_absoluts"]
instrument_values = configdata("instrument.values")
showcase_values = configdata("cf_showcase.showcase_values")
optic_values = configdata("cf_optic.optic_values")

tango_base = instrument_values["tango_base"]
code_base = instrument_values["code_base"]

devices = dict(
    nok2=device(
        code_base + "nok_support.DoubleMotorNOK",
        # length: 300.0 mm
        description="NOK2",
        fmtstr="%.2f, %.2f",
        nok_start=334.0,
        nok_end=634.0,
        nok_gap=1.0,
        inclinationlimits=(-7.4, 11.1),
        motor_r="nok2r_axis",
        motor_s="nok2s_axis",
        nok_motor=[408.5, 585.0],
        precision=0.0,
        masks={
            "ng": optic_values["ng"],
            "rc": optic_values["ng"],
            "vc": optic_values["ng"],
            "fc": optic_values["ng"],
        },
    ),
    # nok2r_brother = device(code_base + 'nok_support.BrotherMotorNOK',
    #      both = 'nok2',
    #      motor = 'nok2r_motor',
    #      brother = 'nok2s_motor',
    #      anlenc = 'nok2r_analog',
    #      index = 1,
    #      unit = '',
    # ),
    # nok2s_brother = device(code_base + 'nok_support.BrotherMotorNOK',
    #      both = 'nok2',
    #      motor = 'nok2s_motor',
    #      brother = 'nok2r_motor',
    #      anlenc = 'nok2s_analog',
    #      index = 0,
    #      unit = '',
    # ),
    nok2r_axis=device(
        "nicos.devices.generic.Axis",
        description="Axis of NOK2, reactor side",
        motor="nok2r_motor",
        # obs = ['nok2r_analog'],
        backlash=-0.5,
        precision=optic_values["precision_ipcsms"],
        unit="mm",
        visibility=(),
    ),
    nok2r_analog=device(
        code_base + "nok_support.NOKPosition",
        description="Position sensing for NOK2, reactor side",
        reference="nok_refa1",
        measure="nok2r_poti",
        # 2020-04-28 15:25:57 poly = [9.169441, 996.418 / 3.858],
        poly=[9.189441, 996.418 / 3.858],
        serial=6510,
        length=250.0,
        visibility=showcase_values["hide_poti"],
    ),
    nok2r_poti=device(
        code_base + "nok_support.NOKMonitoredVoltage",
        description="Poti for NOK2, reactor side",
        tangodevice=tango_base + "test/wb_a/1_1",
        scale=1,  # mounted from bottom
        visibility=(),
    ),
    nok2r_acc=device(
        code_base + "accuracy.Accuracy",
        description="calc error Motor and poti",
        motor="nok2r_motor",
        analog="nok2r_analog",
        visibility=showcase_values["hide_acc"],
        unit="mm",
    ),
    nok2s_axis=device(
        "nicos.devices.generic.Axis",
        description="Axis of NOK2, sample side",
        motor="nok2s_motor",
        # obs = ['nok2s_analog'],
        backlash=-0.5,
        precision=optic_values["precision_ipcsms"],
        unit="mm",
        visibility=(),
    ),
    nok2s_analog=device(
        code_base + "nok_support.NOKPosition",
        description="Position sensing for NOK2, sample side",
        reference="nok_refa1",
        measure="nok2s_poti",
        poly=[-22.686241, 1003.096 / 3.846],
        serial=6512,
        length=250.0,
        visibility=showcase_values["hide_poti"],
    ),
    nok2s_poti=device(
        code_base + "nok_support.NOKMonitoredVoltage",
        description="Poti for NOK2, sample side",
        tangodevice=tango_base + "test/wb_a/1_2",
        scale=1,  # mounted from bottom
        visibility=(),
    ),
    nok2s_acc=device(
        code_base + "accuracy.Accuracy",
        description="calc error Motor and poti",
        motor="nok2s_motor",
        analog="nok2s_analog",
        visibility=showcase_values["hide_acc"],
        unit="mm",
    ),
)

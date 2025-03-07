description = "The Lakeshore 224 Temperature Monitor."

pv_root = "SE-SEE:SE-LS224-001:"

devices = dict(
    T_ls224_A=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel A temperature reading",
        readpv="{}KRDGA".format(pv_root),
    ),
    S_ls224_A=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel A sensor reading",
        readpv="{}SRDGA".format(pv_root),
    ),
    T_ls224_B=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel B temperature reading",
        readpv="{}KRDGB".format(pv_root),
    ),
    S_ls224_B=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel B sensor reading",
        readpv="{}SRDGB".format(pv_root),
    ),
    T_ls224_C1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C1 temperature reading",
        readpv="{}KRDGC1".format(pv_root),
    ),
    S_ls224_C1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C1 sensor reading",
        readpv="{}SRDGC1".format(pv_root),
    ),
    T_ls224_C2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C2 temperature reading",
        readpv="{}KRDGC2".format(pv_root),
    ),
    S_ls224_C2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C2 sensor reading",
        readpv="{}SRDGC2".format(pv_root),
    ),
    T_ls224_C3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C3 temperature reading",
        readpv="{}KRDGC3".format(pv_root),
    ),
    S_ls224_C3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C3 sensor reading",
        readpv="{}SRDGC3".format(pv_root),
    ),
    T_ls224_C4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C4 temperature reading",
        readpv="{}KRDGC4".format(pv_root),
    ),
    S_ls224_C4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C4 sensor reading",
        readpv="{}SRDGC4".format(pv_root),
    ),
    T_ls224_C5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C5 temperature reading",
        readpv="{}KRDGC5".format(pv_root),
    ),
    S_ls224_C5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C5 sensor reading",
        readpv="{}SRDGC5".format(pv_root),
    ),
    T_ls224_D1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D1 temperature reading",
        readpv="{}KRDGD1".format(pv_root),
    ),
    S_ls224_D1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D1 sensor reading",
        readpv="{}SRDGD1".format(pv_root),
    ),
    T_ls224_D2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D2 temperature reading",
        readpv="{}KRDGD2".format(pv_root),
    ),
    S_ls224_D2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D2 sensor reading",
        readpv="{}SRDGD2".format(pv_root),
    ),
    T_ls224_D3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D3 temperature reading",
        readpv="{}KRDGD3".format(pv_root),
    ),
    S_ls224_D3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D3 sensor reading",
        readpv="{}SRDGD3".format(pv_root),
    ),
    T_ls224_D4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D4 temperature reading",
        readpv="{}KRDGD4".format(pv_root),
    ),
    S_ls224_D4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D4 sensor reading",
        readpv="{}SRDGD4".format(pv_root),
    ),
    T_ls224_D5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D5 temperature reading",
        readpv="{}KRDGD5".format(pv_root),
    ),
    S_ls224_D5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D5 sensor reading",
        readpv="{}SRDGD5".format(pv_root),
    ),
    ls224_firmware=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The device firmware",
        readpv="{}FIRMWARE".format(pv_root),
        visibility=(),
    ),
    ls224_model=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The device model",
        readpv="{}MODEL".format(pv_root),
        visibility=(),
    ),
    ls224_serial=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The serial number",
        readpv="{}SERIAL".format(pv_root),
        visibility=(),
    ),
    ls224_curve_file=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The name of the curve file",
        readpv="{}CurveFile:Filename".format(pv_root),
    ),
)

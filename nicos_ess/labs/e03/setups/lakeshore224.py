description = "The Lakeshore 224 Temperature Monitor."

pv_root = "SE-SEE:SE-LS224-001:"

devices = dict(
    T_ls224_A=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel A temperature reading",
        readpv=f"{pv_root}KRDGA",
    ),
    S_ls224_A=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel A sensor reading",
        readpv=f"{pv_root}SRDGA",
    ),
    T_ls224_B=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel B temperature reading",
        readpv=f"{pv_root}KRDGB",
    ),
    S_ls224_B=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel B sensor reading",
        readpv=f"{pv_root}SRDGB",
    ),
    T_ls224_C1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C1 temperature reading",
        readpv=f"{pv_root}KRDGC1",
    ),
    S_ls224_C1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C1 sensor reading",
        readpv=f"{pv_root}SRDGC1",
    ),
    T_ls224_C2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C2 temperature reading",
        readpv=f"{pv_root}KRDGC2",
    ),
    S_ls224_C2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C2 sensor reading",
        readpv=f"{pv_root}SRDGC2",
    ),
    T_ls224_C3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C3 temperature reading",
        readpv=f"{pv_root}KRDGC3",
    ),
    S_ls224_C3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C3 sensor reading",
        readpv=f"{pv_root}SRDGC3",
    ),
    T_ls224_C4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C4 temperature reading",
        readpv=f"{pv_root}KRDGC4",
    ),
    S_ls224_C4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C4 sensor reading",
        readpv=f"{pv_root}SRDGC4",
    ),
    T_ls224_C5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C5 temperature reading",
        readpv=f"{pv_root}KRDGC5",
    ),
    S_ls224_C5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel C5 sensor reading",
        readpv=f"{pv_root}SRDGC5",
    ),
    T_ls224_D1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D1 temperature reading",
        readpv=f"{pv_root}KRDGD1",
    ),
    S_ls224_D1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D1 sensor reading",
        readpv=f"{pv_root}SRDGD1",
    ),
    T_ls224_D2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D2 temperature reading",
        readpv=f"{pv_root}KRDGD2",
    ),
    S_ls224_D2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D2 sensor reading",
        readpv=f"{pv_root}SRDGD2",
    ),
    T_ls224_D3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D3 temperature reading",
        readpv=f"{pv_root}KRDGD3",
    ),
    S_ls224_D3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D3 sensor reading",
        readpv=f"{pv_root}SRDGD3",
    ),
    T_ls224_D4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D4 temperature reading",
        readpv=f"{pv_root}KRDGD4",
    ),
    S_ls224_D4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D4 sensor reading",
        readpv=f"{pv_root}SRDGD4",
    ),
    T_ls224_D5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D5 temperature reading",
        readpv=f"{pv_root}KRDGD5",
    ),
    S_ls224_D5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Channel D5 sensor reading",
        readpv=f"{pv_root}SRDGD5",
    ),
    ls224_firmware=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The device firmware",
        readpv=f"{pv_root}FIRMWARE",
        visibility=(),
    ),
    ls224_model=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The device model",
        readpv=f"{pv_root}MODEL",
        visibility=(),
    ),
    ls224_serial=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The serial number",
        readpv=f"{pv_root}SERIAL",
        visibility=(),
    ),
    ls224_curve_file=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="The name of the curve file",
        readpv=f"{pv_root}CurveFile:Filename",
    ),
)

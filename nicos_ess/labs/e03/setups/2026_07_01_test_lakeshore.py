description = "The Lakeshore Temperature Monitor."

pv_root = "se-aux-204:"

devices = dict(
    c_valve_target=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="",
        readpv=f"{pv_root}CValve-r",
        writepv=f"{pv_root}CValve-Target-s",
    ),
    flush_state=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="",
        readpv=f"{pv_root}Flush-State-r",
    ),
    flush_start=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="",
        readpv=f"{pv_root}Flush-start-s",
        writepv=f"{pv_root}Flush-start-s",
    ),
    ln2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="",
        readpv=f"{pv_root}LN2-r",
    ),
    ln2f_auto=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="",
        readpv=f"{pv_root}LN2F-Auto-s",
        writepv=f"{pv_root}LN2F-Auto-s",
    ),
    temp_b=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="",
        readpv=f"{pv_root}TempB-r",
    ),
    temp_c=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="",
        readpv=f"{pv_root}TempC-r",
    ),
    temp_d=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="",
        readpv=f"{pv_root}TempD-r",
    ),
    pump1_state=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="",
        readpv=f"{pv_root}Pump1-state-s",
        writepv=f"{pv_root}Pump1-state-s",
    ),
    pump2_state=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="",
        readpv=f"{pv_root}Pump2-state-s",
        writepv=f"{pv_root}Pump2-state-s",
    ),
    # T_ls224_A=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel A temperature reading",
    #     readpv="{}KRDGA".format(pv_root),
    # ),
    # S_ls224_A=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel A sensor reading",
    #     readpv="{}SRDGA".format(pv_root),
    # ),
    # T_ls224_B=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel B temperature reading",
    #     readpv="{}KRDGB".format(pv_root),
    # ),
    # S_ls224_B=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel B sensor reading",
    #     readpv="{}SRDGB".format(pv_root),
    # ),
    # T_ls224_C1=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C1 temperature reading",
    #     readpv="{}KRDGC1".format(pv_root),
    # ),
    # S_ls224_C1=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C1 sensor reading",
    #     readpv="{}SRDGC1".format(pv_root),
    # ),
    # T_ls224_C2=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C2 temperature reading",
    #     readpv="{}KRDGC2".format(pv_root),
    # ),
    # S_ls224_C2=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C2 sensor reading",
    #     readpv="{}SRDGC2".format(pv_root),
    # ),
    # T_ls224_C3=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C3 temperature reading",
    #     readpv="{}KRDGC3".format(pv_root),
    # ),
    # S_ls224_C3=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C3 sensor reading",
    #     readpv="{}SRDGC3".format(pv_root),
    # ),
    # T_ls224_C4=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C4 temperature reading",
    #     readpv="{}KRDGC4".format(pv_root),
    # ),
    # S_ls224_C4=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C4 sensor reading",
    #     readpv="{}SRDGC4".format(pv_root),
    # ),
    # T_ls224_C5=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C5 temperature reading",
    #     readpv="{}KRDGC5".format(pv_root),
    # ),
    # S_ls224_C5=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel C5 sensor reading",
    #     readpv="{}SRDGC5".format(pv_root),
    # ),
    # T_ls224_D1=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D1 temperature reading",
    #     readpv="{}KRDGD1".format(pv_root),
    # ),
    # S_ls224_D1=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D1 sensor reading",
    #     readpv="{}SRDGD1".format(pv_root),
    # ),
    # T_ls224_D2=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D2 temperature reading",
    #     readpv="{}KRDGD2".format(pv_root),
    # ),
    # S_ls224_D2=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D2 sensor reading",
    #     readpv="{}SRDGD2".format(pv_root),
    # ),
    # T_ls224_D3=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D3 temperature reading",
    #     readpv="{}KRDGD3".format(pv_root),
    # ),
    # S_ls224_D3=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D3 sensor reading",
    #     readpv="{}SRDGD3".format(pv_root),
    # ),
    # T_ls224_D4=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D4 temperature reading",
    #     readpv="{}KRDGD4".format(pv_root),
    # ),
    # S_ls224_D4=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D4 sensor reading",
    #     readpv="{}SRDGD4".format(pv_root),
    # ),
    # T_ls224_D5=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D5 temperature reading",
    #     readpv="{}KRDGD5".format(pv_root),
    # ),
    # S_ls224_D5=device(
    #     "nicos_ess.devices.epics.pva.EpicsReadable",
    #     description="Channel D5 sensor reading",
    #     readpv="{}SRDGD5".format(pv_root),
    # ),
    # ls224_firmware=device(
    #     "nicos_ess.devices.epics.pva.EpicsStringReadable",
    #     description="The device firmware",
    #     readpv="{}FIRMWARE".format(pv_root),
    #     visibility=(),
    # ),
    # ls224_model=device(
    #     "nicos_ess.devices.epics.pva.EpicsStringReadable",
    #     description="The device model",
    #     readpv="{}MODEL".format(pv_root),
    #     visibility=(),
    # ),
    # ls224_serial=device(
    #     "nicos_ess.devices.epics.pva.EpicsStringReadable",
    #     description="The serial number",
    #     readpv="{}SERIAL".format(pv_root),
    #     visibility=(),
    # ),
    # ls224_curve_file=device(
    #     "nicos_ess.devices.epics.pva.EpicsStringReadable",
    #     description="The name of the curve file",
    #     readpv="{}CurveFile:Filename".format(pv_root),
    # ),
)

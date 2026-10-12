description = "Motion Cabinets"

pv_root_cabinet_1 = "SKADI-MCS1:MC-MCU-01:"
pv_root_cabinet_2 = "SKADI-MCS2:MC-MCU-02:"
pv_root_cabinet_3 = "SKADI-MCS3:MC-MCU-03:"
pv_root_cabinet_4 = "SKADI-MCS4:MC-MCU-04:"
pv_root_cabinet_5 = "SKADI-MCS5:MC-MCU-05:"

devices = dict(
    cabinet_1_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 1 status",
        pv_root=f"{pv_root_cabinet_2}Cabinet",
        number_of_bits=24,
    ),
    cabinet_1_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 1",
        readpv=f"{pv_root_cabinet_2}Pressure1",
    ),
    cabinet_1_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 1 pressure 2",
        readpv=f"{pv_root_cabinet_2}Pressure2",
    ),
    cabinet_2_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 2 status",
        pv_root=f"{pv_root_cabinet_2}Cabinet",
        number_of_bits=24,
    ),
    cabinet_2_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 1",
        readpv=f"{pv_root_cabinet_2}Pressure1",
    ),
    cabinet_2_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 2 pressure 2",
        readpv=f"{pv_root_cabinet_2}Pressure2",
    ),
    cabinet_3_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 3 status",
        pv_root=f"{pv_root_cabinet_3}Cabinet",
        number_of_bits=24,
    ),
    # cabinet_3_pressure_1=device(
    #    "nicos_ess.devices.epics.pva.EpicsReadable",
    #    description="Cabinet 3 pressure 1",
    #    readpv=f"{pv_root_cabinet_3}Pressure1",
    # ),
    # cabinet_3_pressure_2=device(
    #    "nicos_ess.devices.epics.pva.EpicsReadable",
    #    description="Cabinet 3 pressure 2",
    #    readpv=f"{pv_root_cabinet_3}Pressure2",
    # ),
    cabinet_4_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 4 status",
        pv_root=f"{pv_root_cabinet_4}Cabinet",
        number_of_bits=24,
    ),
    # cabinet_4_pressure_1=device(
    #    "nicos_ess.devices.epics.pva.EpicsReadable",
    #    description="Cabinet 4 pressure 1",
    #    readpv=f"{pv_root_cabinet_4}Pressure1",
    # ),
    # cabinet_4_pressure_2=device(
    #    "nicos_ess.devices.epics.pva.EpicsReadable",
    #    description="Cabinet 4 pressure 2",
    #    readpv=f"{pv_root_cabinet_4}Pressure2",
    # ),
    cabinet_4_safety=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 4 safety status",
        pv_root=f"{pv_root_cabinet_4}Safety",
        number_of_bits=24,
    ),
    cabinet_5_status=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 5 status",
        pv_root=f"{pv_root_cabinet_5}Cabinet",
        number_of_bits=24,
    ),
    cabinet_5_pressure_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 5 pressure 1",
        readpv=f"{pv_root_cabinet_5}Pressure1",
    ),
    cabinet_5_pressure_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Cabinet 5 pressure 2",
        readpv=f"{pv_root_cabinet_5}Pressure2",
    ),
    cabinet_5_safety=device(
        "nicos_ess.devices.epics.mbbi_direct.MBBIDirectStatus",
        description="Cabinet 5 safety status",
        pv_root=f"{pv_root_cabinet_5}Safety",
        number_of_bits=24,
    ),
)

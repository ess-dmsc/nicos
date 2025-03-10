description = "MOXA box controlling intensifier intensities"

pv_root = "YMIR-SEE:SC-IOC-008:"

devices = dict(
    ch_0=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 0",
        readpv="{}AO0".format(pv_root),
        writepv="{}AO0Set".format(pv_root),
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
    ch_1=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 1",
        readpv="{}AO1".format(pv_root),
        writepv="{}AO1Set".format(pv_root),
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
    ch_2=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 2",
        readpv="{}AO2".format(pv_root),
        writepv="{}AO2Set".format(pv_root),
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
    ch_3=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 3",
        readpv="{}AO3".format(pv_root),
        writepv="{}AO3Set".format(pv_root),
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
)

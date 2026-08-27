description = "MOXA box controlling intensifier intensities"

pv_root = "YMIR-SEE:SC-IOC-008:"

devices = dict(
    ch_0=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 0",
        readpv=f"{pv_root}AO0",
        writepv=f"{pv_root}AO0Set",
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
    ch_1=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 1",
        readpv=f"{pv_root}AO1",
        writepv=f"{pv_root}AO1Set",
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
    ch_2=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 2",
        readpv=f"{pv_root}AO2",
        writepv=f"{pv_root}AO2Set",
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
    ch_3=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="Channel 3",
        readpv=f"{pv_root}AO3",
        writepv=f"{pv_root}AO3Set",
        abslimits=(0, 10),
        userlimits=(0, 5),
    ),
)

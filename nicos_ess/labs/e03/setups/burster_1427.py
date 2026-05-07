description = "Burster precision resistance decade 1427 (resistance bridge)"

pv_root = "SE-SEE:SE-BU1427-001:"

devices = dict(
    burster_value=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="The resistance?",
        readpv=f"{pv_root}value_RBV",
        writepv=f"{pv_root}value",
        abslimits=(-1e308, 1e308),
    ),
    burster_function=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The current burster function",
        readpv=f"{pv_root}function_RBV",
    ),
    burster_function_set=device(
        "nicos.devices.epics.pva.EpicsMappedMoveable",
        description="Set the burster function",
        readpv=f"{pv_root}function",
        writepv=f"{pv_root}function",
    ),
    burster_idn=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The IDN of the device",
        readpv=f"{pv_root}idn",
    ),
    burster_r0=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="The resistance",
        readpv=f"{pv_root}r0_RBV",
        writepv=f"{pv_root}r0",
        abslimits=(-1e308, 1e308),
    ),
    burster_status=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The status",
        readpv=f"{pv_root}status_RBV",
    ),
    burster_terminal_r=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="The resistance",
        readpv=f"{pv_root}terminal_RBV",
        writepv=f"{pv_root}terminal",
        abslimits=(-1e308, 1e308),
    ),
)

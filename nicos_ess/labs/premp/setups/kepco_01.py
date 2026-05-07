description = "Kepco power supply"

pv_root = "utg-kepco-001:"

devices = dict(
    IDN_kepco=device(
        "nicos.devices.epics.pva.EpicsStringReadable",
        description="The hardware Identification",
        readpv=f"{pv_root}IDN_rbv",
    ),
    V_kepco=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        description="The Voltage",
        readpv=f"{pv_root}MeasVolt",
        writepv=f"{pv_root}Volt",
        targetpv=f"{pv_root}Volt_rbv",
    ),
    Remote_kepco=device(
        "nicos.devices.epics.pva.EpicsMappedMoveable",
        description="Setting remote mode on/off",
        readpv=f"{pv_root}Remote_rbv",
        writepv=f"{pv_root}Remote",
    ),
    Output_kepco=device(
        "nicos.devices.epics.pva.EpicsMappedMoveable",
        description="Setting output on/off",
        readpv=f"{pv_root}Output_rbv",
        writepv=f"{pv_root}Output",
    ),
)

description = "Julabo F25 for the Huginn-sans."

pv_root = "SES-HGNSANS-01:WTctrl-JUL25HL-001:"

devices = dict(
    T_julabo=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The temperature",
        readpv=f"{pv_root}TEMP",
        writepv=f"{pv_root}TEMP:SP1",
        targetpv=f"{pv_root}TEMP:SP1:RBV",
    ),
    julabo_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="The status",
        readpv=f"{pv_root}MODE",
        writepv=f"{pv_root}MODE:SP",
    ),
    T_julabo_external=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The external sensor temperature",
        readpv=f"{pv_root}EXTT",
        visibility=(),
    ),
    julabo_external_enabled=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Whether the external sensor is enabled",
        readpv=f"{pv_root}EXTSENS",
        visibility=(),
    ),
    julabo_internal_P=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal P value",
        readpv=f"{pv_root}INTP",
        writepv=f"{pv_root}INTP:SP",
        visibility=(),
    ),
    julabo_internal_I=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal I value",
        readpv=f"{pv_root}INTI",
        writepv=f"{pv_root}INTI:SP",
        visibility=(),
    ),
    julabo_internal_D=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The internal D value",
        readpv=f"{pv_root}INTD",
        writepv=f"{pv_root}INTD:SP",
        visibility=(),
    ),
)

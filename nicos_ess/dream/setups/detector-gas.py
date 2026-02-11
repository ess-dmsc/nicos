description = "Monitor detector pressure"

devices = dict(
    bundle_left_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Gas pressure of left detector bundle",
        readpv="DREAM-DtCmn:GaD-001:AI0User",
        unit="bar",
    ),
    bundle_right_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Gas pressure of right detector bundle",
        readpv="DREAM-DtCmn:GaD-001:AI1User",
        unit="bar",
    ),
    cave_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Gas pressure in detector cave",
        readpv="DREAM-DtCmn:GaD-001:AI3User",
        unit="bar",
    ),
)

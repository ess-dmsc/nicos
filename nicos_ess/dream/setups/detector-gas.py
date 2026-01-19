description = "Monitor detector pressure"

devices = dict(
    bundle_left_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Detector bundle left gas pressure",
        readpv="DREAM-DtCmn:GaD-001:AI0",
    ),
    bundle_right_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Detector bundle right gas pressure",
        readpv="DREAM-DtCmn:GaD-001:AI1",
    ),
    cave_pressure=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Detector cave gas pressure",
        readpv="DREAM-DtCmn:GaD-001:AI3",
    ),
)
description = "minimal EPICS setup for integration smoke checks"

group = "lowlevel"

modules = ["nicos.commands.standard", "nicos_ess.commands"]

devices = dict(
    SmokeBasicReadable=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsReadable",
        description="Basic smoke EPICS readable",
        readpv="TEST:SMOKE:READ.RBV",
        monitor=True,
        pva=True,
    ),
    SmokeBasicMoveable=device(
        "nicos_ess.devices.epics.pva.epics_devices.EpicsAnalogMoveable",
        description="Basic smoke EPICS analog moveable",
        readpv="TEST:SMOKE:MOVE.RBV",
        writepv="TEST:SMOKE:MOVE.VAL",
        monitor=True,
        pva=True,
        unit="Hz",
        precision=0.01,
    ),
)

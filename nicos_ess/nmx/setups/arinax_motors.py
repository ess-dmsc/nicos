description = "ARINAX sample motors (from the mockup software)"

group = "basic"

devices = dict(
    phi=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="ARINAX sample motor Phi (mockup)",
        readpv="NMX:PhiPosition",
        writepv="NMX:PhiPosition",
        unit="mm",
        pva=False,
    ),
)

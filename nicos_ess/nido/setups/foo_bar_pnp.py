# ruff: noqa: F821
description = "A little device to test pnp_listener"

pnp_pv_root = "foo:bar"

devices = dict(
    heartbeat_read=device(
        "nicos.devices.epics.pva.EpicsReadable",
        description="Heartbeat readback",
        readpv=f"{pnp_pv_root}:PNPHeartBeatCnt-S",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
)

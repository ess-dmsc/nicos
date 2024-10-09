# ruff: noqa: F821
description = "A little device to test pnp_listener"

group = "plugplay"
pnp_pv_root = "foo:bar"

devices = dict(
    heartbeat_read=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="Heartbeat readback",
        readpv=f"{pnp_pv_root}:PNPHeartBeatCnt-S",
        pva=True,
        monitor=True,
        pollinterval=None,
        maxage=None,
    ),
)

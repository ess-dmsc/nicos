# ruff: noqa: F821
description = "A little device to test pnp_listener"

group = "plugplay"
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
        nexus_config=[
            {
                "group_name": "foobar",
                "nx_class": "NXcollection",
                "units": "",
                "suffix": "readback",
                "source_name": f"{pnp_pv_root}:PNPHeartBeatCnt-S",
                "schema": "f144",
                "topic": "bifrost_motion",
                "protocol": "pva",
                "periodic": 1,
            },
        ],
    ),
)

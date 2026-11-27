description = "The Knauer Azura valve."

group = "plugplay"

extended = dict(
    presence_signal="pva://SE-SEE:SE-KVU-001:Position-RB",
)

devices = dict(
    KV=device(
        "nicos_ess.loki.devices.knauer_valve.KnauerValve",
        description=".",
        pvroot="SE-SEE:SE-KVU-001:",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
)

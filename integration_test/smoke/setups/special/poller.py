description = "setup for the poller (smoke integration)"
group = "special"

sysconfig = dict(
    cache=configdata("config.CACHE_HOST"),
)

devices = dict(
    Poller=device(
        "nicos.services.poller.Poller",
        alwayspoll=[],
        neverpoll=[],
        blacklist=[],
    ),
)

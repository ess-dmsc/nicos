description = "setup for the poller"
group = "special"

sysconfig = dict(
    # use only 'localhost' if the cache is really running on the same machine,
    # otherwise use the official computer name
    cache="localhost"
)

devices = dict(
    Poller=device(
        "nicos.services.poller.Poller",
        # setups that should be polled regardless if loaded; the plug-and-play
        # presence must be watched even before any setup is loaded
        alwayspoll=["sample_environment_presence"],
        neverpoll=[],  # setups that should not be polled even if loaded
        blacklist=[],  # DEVICES that should never be polled
        # (usually detectors or devices that have problems
        # with concurrent access from processes)
    ),
)

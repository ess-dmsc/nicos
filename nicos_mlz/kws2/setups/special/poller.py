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
        alwayspoll=["memograph"],
        neverpoll=[],
        blacklist=[],  # DEVICES that should never be polled
        # (usually detectors or devices that have problems
        # with concurrent access from processes)
    ),
)

# Always import pyepics in the main thread first.
startupcode = """
import nicos.devices.epics.pyepics
"""

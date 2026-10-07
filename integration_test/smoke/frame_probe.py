"""Report NICOS frames whose locals would leak a canary into a traceback.

The smoke runner installs this module as ``sitecustomize`` for the NICOS
services, so every service process loads it at startup.

NICOS log files contain the local variables of every ``nicos*`` frame of a
traceback. A credential held in a local therefore leaks as soon as anything
raises in that function. This checks the locals of each frame when the frame
exits, which finds those functions without the exception having to happen.

A local that holds a canary is rendered with the formatter the log files use.
If the canary survives that, the line is written to the log directory, where
the canary scan of the runner picks it up.
"""

import os
import sys
from types import SimpleNamespace

from nicos.utils import formatExtendedFrame

CANARIES = os.environ["NICOS_SMOKE_CANARIES"].split()
REPORT = os.path.join(
    os.environ["NICOS_SMOKE_RUNTIME_ROOT"], "log", f"frame-locals-{os.getpid()}.log"
)
reported = set()


def holds_canary(value, depth=3):
    """Search plain containers only: the repr of an arbitrary object may block."""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    if isinstance(value, str):
        return any(canary in value for canary in CANARIES)
    if isinstance(value, dict):
        value = value.values()
    elif not isinstance(value, (list, tuple, set, frozenset)):
        return False
    return depth > 0 and any(holds_canary(item, depth - 1) for item in value)


def check_frame(code, frame):
    suspects = {
        name: value for name, value in frame.f_locals.items() if holds_canary(value)
    }
    for line in formatExtendedFrame(SimpleNamespace(f_locals=suspects)):
        if (code, line) not in reported and holds_canary(line):
            reported.add((code, line))
            with open(REPORT, "a", encoding="utf-8") as report:
                report.write(
                    f"{code.co_filename}:{code.co_firstlineno} "
                    f"{code.co_qualname}: {line.strip()}\n"
                )


def is_nicos(frame):
    return (frame.f_globals.get("__name__") or "").startswith("nicos")


def on_return(code, *_):
    frame = sys._getframe(1)
    if not is_nicos(frame):
        # Stops the events for this function, which keeps the probe cheap.
        return sys.monitoring.DISABLE
    check_frame(code, frame)


def on_unwind(code, *_):
    frame = sys._getframe(1)
    if is_nicos(frame):
        check_frame(code, frame)


events = sys.monitoring.events
sys.monitoring.use_tool_id(sys.monitoring.PROFILER_ID, "canary frame probe")
sys.monitoring.register_callback(
    sys.monitoring.PROFILER_ID, events.PY_RETURN, on_return
)
sys.monitoring.register_callback(
    sys.monitoring.PROFILER_ID, events.PY_UNWIND, on_unwind
)
sys.monitoring.set_events(
    sys.monitoring.PROFILER_ID, events.PY_RETURN | events.PY_UNWIND
)

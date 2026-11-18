"""esslivedata's messages, read without esslivedata.

Wire formats (esslivedata ``main`` 2026-11):

* heartbeats, x5f2 on ``<instrument>_livedata_heartbeat``: ``status_json``
  holds a message of type ``job`` (one job's state) or ``service`` (one
  backend worker);
* outputs are da00 holding a scipp DataArray: ``signal`` (its ``label`` is
  the name), ``errors`` as standard deviations, one variable per coordinate;
  on ``<instrument>_livedata_data`` their source name is the JSON result key
  (workflow, job, output name).
* commands are JSON on ``<instrument>_livedata_commands``. Each service that
  acted on a command answers with ACK or ERR on
  ``<instrument>_livedata_responses`` and echoes the ``message_id`` of the
  command.
"""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
from streaming_data_types.status_x5f2 import deserialise_x5f2
from streaming_data_types.utils import get_schema

from nicos.core import status
from nicos_ess.utilities.live_frame import Coord, Frame

#: esslivedata puts these scalar times on every output. They are the start of
#: the accumulation and the time of the newest data in it.
TIME_STAMPS = ("start_time", "time")

#: These are the years 2000 to 2100 in epoch seconds. A time stamp in a wrong
#: unit lies far outside them, because the units differ by factors of 1000.
PLAUSIBLE_TIMES = (946_684_800, 4_102_444_800)

#: The longest heartbeat interval in seconds that NICOS believes. A longer one
#: is in another unit and would keep a dead job alive.
LONGEST_INTERVAL = 60


def responses_topic(commands_topic):
    """Return the topic where esslivedata answers the commands on *commands_topic*."""
    return commands_topic.removesuffix("commands") + "responses"


def parse_heartbeat(raw):
    """What a x5f2 heartbeat reports: ("job", job), ("service", service),
    or None for anything else. ``interval`` is how often it comes (s); a
    job's ``status`` is the NICOS status its service gives it."""
    if get_schema(raw) != "x5f2":
        return None
    st = deserialise_x5f2(raw)
    payload = json.loads(st.status_json) if st.status_json else {}
    message = payload.get("message") or {}
    kind = message.get("message_type", "job")
    interval = min(max(1.0, st.update_interval / 1000.0), LONGEST_INTERVAL)
    if kind == "service":
        return "service", dict(
            service=message["service_name"],
            worker=message.get("worker_id", st.service_id),
            state=message["state"],
            jobs=int(message.get("active_job_count", 0)),
            message=str(message.get("error") or ""),
            interval=interval,
        )
    if kind != "job" or "job_id" not in message:
        return None
    job = message["job_id"]
    return "job", dict(
        workflow_id=message["workflow_id"],
        source_name=job["source_name"],
        job_number=str(job["job_number"]),
        state=message["state"],
        message=str(message.get("error") or message.get("warning") or ""),
        status=int(payload["status"]),
        interval=interval,
    )


def job_health(job):
    """Return the NICOS status and a text for a parsed job heartbeat.

    An UNKNOWN status counts as an error.
    """
    code = job["status"]
    if code == status.UNKNOWN:
        code = status.ERROR
    text = "" if code == status.OK else job["message"] or f"Job {job['state']}"
    return code, text


def headline(message):
    """Return the last line of an esslivedata error message.

    A traceback ends with the line that says what went wrong.
    """
    return message.strip().rsplit("\n", 1)[-1]


def parse_ack(raw):
    """Parse an answer to a command into a dict with message_id, ok and message.

    ok is True for ACK and False for ERR. Anything that is not an answer raises
    ValueError.
    """
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"not an answer: {payload!r}")
    return dict(
        message_id=payload.get("message_id"),
        ok=payload.get("response") == "ACK",
        message=str(payload.get("message") or ""),
    )


def time_stamp(var):
    """Return a scalar da00 time in s, ms, us or ns, or in ``datetime64`` of
    these units, in epoch seconds.

    Return None for any other variable and for a time outside PLAUSIBLE_TIMES.
    """
    unit = (var.unit or "").removeprefix("datetime64[").removesuffix("]")
    values = np.asarray(var.data)
    if var.axes or values.size != 1 or unit not in ("s", "ms", "us", "ns"):
        return None
    seconds = int(values.reshape(())) * (
        np.timedelta64(1, unit) / np.timedelta64(1, "s")
    )
    low, high = PLAUSIBLE_TIMES
    return seconds if low < seconds < high else None


def frame_from_da00(by_name, title=""):
    """Return the `Frame` of an output, given its variables by name.

    An output without a valid signal raises ValueError. Coordinates that do not fit
    the dims of the signal are left out, as the esslivedata reader does. The
    time stamps go into ``meta``.
    """
    sig = by_name.get("signal")
    if sig is None:
        raise ValueError(f"no signal, only {', '.join(by_name)}")
    data = np.asarray(sig.data)
    dims = tuple(sig.axes or ())
    if data.ndim == 0:
        data, dims = data.reshape(1), dims[:1] or ("dim_0",)
    errors = by_name.get("errors")
    errors = None if errors is None else np.asarray(errors.data)
    frame = Frame(
        data,
        dims,
        unit=sig.unit or "",
        title=(sig.label or "").strip() or title,
        errors=errors if errors is not None and errors.shape == data.shape else None,
    )
    coords, meta = {}, {}
    for name, var in by_name.items():
        if name in TIME_STAMPS and (stamp := time_stamp(var)) is not None:
            meta[name] = stamp
        elif name not in ("signal", "errors") and var.axes:
            coord = Coord(tuple(var.axes), np.asarray(var.data), var.unit or "")
            if coord.fits(frame.sizes):
                coords[name] = coord
    return replace(frame, coords=coords, meta=meta)

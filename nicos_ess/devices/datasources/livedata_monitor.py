"""esslivedata as seen from NICOS, with its jobs and services."""

from __future__ import annotations

import threading
import time
from uuid import uuid4

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Override,
    Param,
    Readable,
    dictof,
    host,
    listof,
    status,
)
from nicos.utils import createThread
from nicos_ess.devices.datasources import livedata_protocol as proto
from nicos_ess.devices.kafka.consumer import KafkaConsumer
from nicos_ess.utilities.limited_warnings import LimitedWarnings


class LiveDataMonitor(Readable):
    """esslivedata's jobs and services, read from Kafka.

    It only reads every job and backend service through their heartbeats.
    esslivedata's results reach NICOS as the channels of a
    `LiveDataCollector`.

    The value is the number of running jobs. The status is the status of the
    worst job, or an error if a backend service fails.
    """

    parameters = {
        "brokers": Param(
            "Kafka brokers",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "instrument": Param(
            "esslivedata instrument name, used as the topic prefix",
            type=str,
            mandatory=True,
            userparam=False,
        ),
        "jobs": Param(
            "The jobs the backend reports, by job key",
            type=dictof(str, dict),
            default={},
            internal=True,
            settable=True,
        ),
        "services": Param(
            "The backend services heard from, by name",
            type=dictof(str, dict),
            default={},
            internal=True,
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="jobs", mandatory=False, settable=False),
        "fmtstr": Override(default="%d"),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    def doPreinit(self, mode):
        self._consumer = self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._warnings = LimitedWarnings(self.log)
        # Both dicts map a job key or a worker id to its expiry time and its
        # last heartbeat.
        self._jobs, self._workers = {}, {}

    def doInit(self, mode):
        if mode == SIMULATION or session.sessiontype == POLLER:
            return
        self._consumer = KafkaConsumer.create(
            self.brokers,
            starting_offset="latest",
            group_id=f"nicos-livedata-{uuid4().hex}",
        )
        self._consumer.subscribe([f"{self.instrument}_livedata_heartbeat"])
        self._thread = createThread(f"{self.name} follower", self._follow)

    def _follow(self):
        published = 0.0
        while not self._stop.is_set():
            try:
                msg = self._consumer.poll(timeout_ms=200)
                if msg is not None and not msg.error():
                    try:
                        self._handle(msg.topic(), msg.value())
                    except Exception as err:
                        self._warnings.warn(
                            msg.topic(), "could not read %s: %s", msg.topic(), err
                        )
                if time.monotonic() - published > 1:
                    published = time.monotonic()
                    self._publish()
            except Exception as err:
                # The thread must survive, otherwise jobs never expire and a
                # dead service looks alive.
                self._warnings.warn("poll", "following esslivedata failed: %s", err)
                self._stop.wait(1)

    def _handle(self, topic, raw):
        parsed = proto.parse_heartbeat(raw)
        if parsed is None:
            return
        kind, beat = parsed
        if kind == "service":
            table, key = self._workers, beat["worker"]
        else:
            table, key = self._jobs, f"{beat['source_name']}/{beat['job_number']}"
        expires = time.monotonic() + 3 * beat.pop("interval")
        with self._lock:
            if beat["state"] == "stopped":
                table.pop(key, None)
            else:
                table[key] = (expires, beat)

    def _publish(self):
        """Put what changed in the cache.

        Jobs that stopped sending heartbeats are dropped. A service stays as
        lost until it sends a heartbeat again.
        """
        now = time.monotonic()
        with self._lock:
            self._jobs = {k: v for k, v in self._jobs.items() if v[0] > now}
            alive = {beat["service"] for t, beat in self._workers.values() if t > now}
            self._workers = {
                k: (t, beat)
                for k, (t, beat) in self._workers.items()
                if t > now or beat["service"] not in alive
            }
            jobs = {k: beat for k, (_, beat) in self._jobs.items()}
            workers = [(t > now, beat) for t, beat in self._workers.values()]
        services = {}
        for heard, w in workers:
            svc = services.setdefault(
                w["service"], dict(workers=0, jobs=0, state="running", message="")
            )
            if not heard:
                svc["state"], svc["message"] = "lost", "no heartbeat"
                continue
            svc["workers"] += 1
            svc["jobs"] += w["jobs"]
            if w["state"] != "running":
                svc["state"], svc["message"] = w["state"], w["message"]
        if jobs != self.jobs or services != self.services:
            self.jobs, self.services = jobs, services
            if self._cache:
                self._cache.put(self, "value", len(jobs), time.time())
                self._cache.put(self, "status", self.doStatus(), time.time())

    def doRead(self, maxage=0):
        return len(self.jobs)

    def doStatus(self, maxage=0):
        return self._service_problem() or self._job_status()

    def _service_problem(self):
        """Return the status of failing or silent services, or None if all run."""
        failing = [
            f"esslivedata service {name}: {svc['message'] or svc['state']}"
            for name, svc in sorted(self.services.items())
            if svc["state"] == "error"
        ]
        if failing:
            return status.ERROR, "; ".join(failing)
        if not self.services:  # Kafka or esslivedata is down or has not started yet
            return status.WARN, "no heartbeat from esslivedata"
        if lost := [n for n, svc in self.services.items() if svc["state"] == "lost"]:
            return status.WARN, f"no heartbeat from esslivedata {', '.join(lost)}"
        return None

    def _job_status(self):
        if not self.jobs:
            return status.OK, "no jobs running"
        worst = max(self.jobs.values(), key=lambda j: proto.job_health(j)[0])
        code, text = proto.job_health(worst)
        if code != status.OK:
            return code, f"{worst['workflow_id']} on {worst['source_name']}: {text}"
        return status.OK, f"{len(self.jobs)} jobs running"

    def doShutdown(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if self._consumer:
            self._consumer.close()

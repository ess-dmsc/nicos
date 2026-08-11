"""
Lightweight helpers for the NICOS ↔ ESSLivedata integration.

- ResultKey parsing (from DA00 source_name JSON)
- Selector parsing (channel "what to follow")
- In-memory JobRegistry (kept up-to-date from status + data)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class WorkflowId:
    def __str__(self):
        """Compact path form used by selectors and UI menus."""
        return f"{self.instrument}/{self.name}/{self.version}"

    instrument: str
    name: str
    version: int


@dataclass(frozen=True)
class JobId:
    source_name: str
    job_number: str  # uuid string


@dataclass(frozen=True)
class ResultKey:
    workflow_id: WorkflowId
    job_id: JobId
    output_name: Optional[str]


def parse_result_key(source_name_json: str) -> ResultKey:
    """Parse DA00 source_name JSON => ResultKey."""
    raw = json.loads(source_name_json)
    wf = raw["workflow_id"]
    job = raw["job_id"]
    return ResultKey(
        workflow_id=WorkflowId(
            instrument=wf["instrument"],
            name=wf["name"],
            version=int(wf["version"]),
        ),
        job_id=JobId(
            source_name=job["source_name"],
            job_number=job["job_number"],
        ),
        output_name=raw.get("output_name"),
    )


@dataclass
class JobInfo:
    workflow_path: str
    job_number: str
    source_name: str
    state: str
    start_time_ns: Optional[int] = None
    end_time_ns: Optional[int] = None
    outputs: Set[str] = field(default_factory=set)
    last_seen_s: float = field(default_factory=lambda: time.time())
    heartbeat_ms: int = 1000


class JobRegistry:
    """
    Keeps an always-up-to-date view of jobs seen via status/data streams.
    Keyed by (source_name, job_number).
    """

    def __init__(self) -> None:
        self._jobs: Dict[Tuple[str, str], JobInfo] = {}

    @staticmethod
    def _key(source_name: str, job_number: str) -> Tuple[str, str]:
        return (source_name, job_number)

    def jobinfo_from_status(
        self,
        wf: WorkflowId | str,
        job_source_name: str,
        job_number: str,
        state: str,
        start_time_ns: Optional[int] = None,
        end_time_ns: Optional[int] = None,
        heartbeat_ms: Optional[int] = None,
    ) -> None:
        if isinstance(wf, str):
            wf_path = wf
        else:
            wf_path = str(wf)

        key = self._key(job_source_name, job_number)
        ji = self._jobs.get(key)
        if ji is None:
            ji = JobInfo(
                workflow_path=wf_path,
                job_number=job_number,
                source_name=job_source_name,
                state=state,
                start_time_ns=start_time_ns,
                end_time_ns=end_time_ns,
            )
            self._jobs[key] = ji
        else:
            ji.state = state
            if start_time_ns is not None:
                ji.start_time_ns = start_time_ns
            if end_time_ns is not None:
                ji.end_time_ns = end_time_ns

        ji.last_seen_s = time.time()
        if heartbeat_ms and heartbeat_ms > 0:
            ji.heartbeat_ms = int(heartbeat_ms)

    def note_output(
        self, wf: WorkflowId, job: JobId, output_name: Optional[str]
    ) -> None:
        if not output_name:
            return
        key = self._key(job.source_name, job.job_number)
        ji = self._jobs.get(key)
        if ji is None:
            ji = JobInfo(
                workflow_path=str(wf),
                job_number=job.job_number,
                source_name=job.source_name,
                state="active",
            )
            self._jobs[key] = ji
        ji.outputs.add(output_name)

    def list_jobs(self) -> List[JobInfo]:
        return list(self._jobs.values())

    def resolve_latest(self, workflow_path: str, source_name: str) -> Optional[JobInfo]:
        """
        Pick the most relevant job: prefer active, then scheduled, then finishing,
        then newest start time.
        """
        candidates = [
            j
            for j in self._jobs.values()
            if j.workflow_path == workflow_path and j.source_name == source_name
        ]
        if not candidates:
            return None
        order = {
            "active": 0,
            "scheduled": 1,
            "finishing": 2,
            "stopped": 3,
            "warning": 4,
            "error": 5,
        }
        return sorted(
            candidates, key=lambda j: (order.get(j.state, 99), -(j.start_time_ns or 0))
        )[0]

    def mark_seen(self, job_source_name: str, job_number: str) -> None:
        """Touch a job when we observe DA00 for it."""
        ji = self._jobs.get(self._key(job_source_name, job_number))
        if ji:
            ji.last_seen_s = time.time()

    def remove_job(self, job_source_name: str, job_number: str) -> None:
        """Explicitly remove a job (e.g. when a response says 'removed')."""
        self._jobs.pop(self._key(job_source_name, job_number), None)

    def expire_stale(self, now: Optional[float] = None, grace_mult: float = 3.0) -> int:
        """
        Remove jobs that missed several heartbeats.
        A job is stale if (now - last_seen) > grace_mult * heartbeat interval.
        Returns how many jobs were removed.
        """
        now = now or time.time()
        todel = []
        for key, ji in self._jobs.items():
            hb_s = max(ji.heartbeat_ms / 1000.0, 1.0)
            if (now - (ji.last_seen_s or 0)) > (grace_mult * hb_s):
                todel.append(key)
        for key in todel:
            del self._jobs[key]
        return len(todel)


@dataclass(frozen=True)
class DeviceSelector:
    """
    A binding to a specific device name from the ESSlivedata device contract.

    This is simpler than Selector - it only needs the device name, as the
    DeviceExtractor in ESSlivedata publishes messages keyed by device name
    to the LIVEDATA_NICOS_DATA topic.

    The device name corresponds to entries in the ESSlivedata device contract,
    e.g., "monitor1_counts_total" for a monitor cumulative count.

    Parameters
    ----------
    device_name : str
        The name of the derived device from the device contract.
    workflow_id : str, optional
        The workflow ID in format "instrument/name/version" that provides
        this device. Used for sending reset commands.
    """

    device_name: str
    workflow_id: Optional[str] = None

    @classmethod
    def parse_device_name(
        cls, s: str, workflow_id: Optional[str] = None
    ) -> DeviceSelector:
        """Create a DeviceSelector from a device name."""
        return cls(device_name=s, workflow_id=workflow_id)

    def matches(self, device_name: str) -> bool:
        """Check if this selector matches a device name."""
        return self.device_name == device_name

    def matches_da00_source(self, source_name: str) -> bool:
        """
        Check if this selector matches the source_name from a DA00 message.

        For NICOS_DATA topic messages, the DeviceExtractor sets the DA00
        source_name to the device name.
        """
        return self.device_name == source_name

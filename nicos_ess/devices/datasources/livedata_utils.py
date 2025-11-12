"""
Lightweight helpers for the NICOS ↔ ESSLivedata integration.

- ResultKey parsing (from DA00 source_name JSON)
- Selector parsing (channel "what to follow")
- In-memory JobRegistry (kept up-to-date from status + data)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class WorkflowId:
    instrument: str
    namespace: str
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
            namespace=wf["namespace"],
            name=wf["name"],
            version=int(wf["version"]),
        ),
        job_id=JobId(
            source_name=job["source_name"],
            job_number=job["job_number"],
        ),
        output_name=raw.get("output_name"),
    )


def workflow_path(wf: WorkflowId) -> str:
    """Compact path form used by selectors and UI menus."""
    return f"{wf.instrument}/{wf.namespace}/{wf.name}/{wf.version}"


@dataclass(frozen=True)
class Selector:
    """
    A concrete binding to a workflow/source (and optionally a specific job/output).

    Format (string):
        "<instrument>/<namespace>/<name>/<version>@<source_name>#<job_number>/<output_name>"

    - '#<job_number>' is optional => will bind to the latest active job.
    - '/<output_name>' is optional => channel may choose a default (e.g. "current").
    """

    workflow_path: str
    source_name: str
    job_number: Optional[str] = None
    output_name: Optional[str] = None


def parse_selector(s: str) -> Selector:
    """
    Parse the selector string. Minimal validation; keeps things permissive for UIs.
    """
    wf_part, rest = s.split("@", 1)
    job_part, slash, out = rest.partition("/")
    src, hashmark, job = job_part.partition("#")
    job_num = job if hashmark else None
    out_name = out if slash else None
    return Selector(
        workflow_path=wf_part, source_name=src, job_number=job_num, output_name=out_name
    )


def selector_to_string(sel: Selector) -> str:
    """Convert a Selector back to its string representation."""
    s = f"{sel.workflow_path}@{sel.source_name}"
    if sel.job_number:
        s += f"#{sel.job_number}"
    if sel.output_name:
        s += f"/{sel.output_name}"
    return s


def selector_matches(sel: Selector, rk: ResultKey) -> bool:
    """Check if a DA00 ResultKey matches a channel selector."""
    if workflow_path(rk.workflow_id) != sel.workflow_path:
        return False
    if rk.job_id.source_name != sel.source_name:
        return False
    if sel.job_number and rk.job_id.job_number != sel.job_number:
        return False
    if sel.output_name and rk.output_name != sel.output_name:
        return False
    return True


@dataclass
class JobInfo:
    workflow_path: str
    job_number: str
    source_name: str
    state: str
    start_time_ns: Optional[int] = None
    end_time_ns: Optional[int] = None
    outputs: Set[str] = field(default_factory=set)


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

    def upsert_from_status(
        self,
        wf: WorkflowId | str,
        job_source_name: str,
        job_number: str,
        state: str,
        start_time_ns: Optional[int] = None,
        end_time_ns: Optional[int] = None,
    ) -> None:
        if isinstance(wf, str):
            wf_path = wf
        else:
            wf_path = workflow_path(wf)

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

    def note_output(
        self, wf: WorkflowId, job: JobId, output_name: Optional[str]
    ) -> None:
        if not output_name:
            return
        key = self._key(job.source_name, job.job_number)
        ji = self._jobs.get(key)
        if ji is None:
            ji = JobInfo(
                workflow_path=workflow_path(wf),
                job_number=job.job_number,
                source_name=job.source_name,
                state="active",
            )
            self._jobs[key] = ji
        ji.outputs.add(output_name)

    def list_jobs(self) -> List[JobInfo]:
        return list(self._jobs.values())

    def resolve_latest(
        self, workflow_path_str: str, source_name: str
    ) -> Optional[JobInfo]:
        """
        Pick the most relevant job: prefer active, then scheduled, then finishing,
        then newest start time.
        """
        candidates = [
            j
            for j in self._jobs.values()
            if j.workflow_path == workflow_path_str and j.source_name == source_name
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

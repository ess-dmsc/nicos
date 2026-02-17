#!/usr/bin/env python3
"""Run a full NICOS smoke stack for EPICS+Kafka integration validation.

Stack components:
- Kafka (docker compose)
- Local in-process PVA server
- nicos-cache
- nicos-poller
- nicos-collector
- nicos-daemon
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from confluent_kafka import KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from p4p.client.thread import Context as PvaContext

# Allow running as a plain script: `python integration_test/smoke/run_smoke_stack.py`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from integration_test.smoke.pva_server import SmokePvaServer
from nicos.clients.base import ConnectionData, NicosClient
from nicos.protocols.daemon import STATUS_IDLE, STATUS_IDLEEXC
from nicos.utils import parseConnectionString

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = SMOKE_ROOT / "docker-compose.kafka.yml"
RUNTIME_ROOT = REPO_ROOT / "integration_test" / "runtime"
LOG_ROOT = RUNTIME_ROOT / "log"

CACHE_HOST = "localhost"
CACHE_PORT = 24869
DAEMON_HOST = "localhost"
DAEMON_PORT = 21301
KAFKA_BOOTSTRAP = "localhost:19092"

SMOKE_TOPICS = [
    "test_smoke_forwarder_dynamic_status",
    "test_smoke_forwarder_dynamic_config",
    "test_smoke_filewriter",
    "test_smoke_filewriter_status",
    "test_smoke_filewriter_pool",
    "test_smoke_scichat",
    "test_smoke_nicos_devices",
]


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen
    logfile_handle: object
    logfile_path: Path


class SmokeClient(NicosClient):
    """Small daemon client with strict error handling for smoke runs."""

    def __init__(self):
        self._disconnecting = False
        super().__init__(print)

    def signal(self, name, data=None, data2=None):
        if name == "error":
            raise RuntimeError(f"daemon client error: {data} ({data2})")
        if name == "broken":
            raise RuntimeError(f"daemon connection broken: {data}")
        if name == "disconnected" and not self._disconnecting:
            raise RuntimeError("daemon disconnected unexpectedly")

    def wait_idle(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            reply = self.ask("getstatus", quiet=True, default=None)
            if reply and reply["status"][0] in (STATUS_IDLE, STATUS_IDLEEXC):
                if reply["status"][0] == STATUS_IDLEEXC:
                    raise RuntimeError(f"daemon idle with exception: {reply['status']}")
                return
            time.sleep(0.1)
        raise TimeoutError("timed out waiting for daemon idle status")

    def execute(self, code: str, *, timeout: float = 60.0) -> int:
        """Execute command/script text and wait for this request to complete."""
        reqid = self.run(code, filename="<smoke-test>", noqueue=True)
        if reqid is None:
            raise RuntimeError(f"failed to execute command: {code!r}")

        deadline = time.monotonic() + timeout
        sync_deadline = min(deadline, time.monotonic() + 5.0)
        seen_activity = False

        # Synchronize on the submitted request to avoid idle-race false returns.
        while time.monotonic() < sync_deadline:
            reply = self.ask("getstatus", quiet=True, default=None)
            if not reply:
                time.sleep(0.05)
                continue
            status_code = reply["status"][0]
            queued = {
                item.get("reqid")
                for item in reply.get("requests", [])
                if isinstance(item, dict)
            }
            if reqid in queued or status_code not in (STATUS_IDLE, STATUS_IDLEEXC):
                seen_activity = True
                break
            time.sleep(0.05)

        if not seen_activity:
            # Request was either very short-lived or not observable in queue/status.
            self.wait_idle(timeout=max(0.1, deadline - time.monotonic()))
            return reqid

        while time.monotonic() < deadline:
            reply = self.ask("getstatus", quiet=True, default=None)
            if not reply:
                time.sleep(0.05)
                continue
            status_code = reply["status"][0]
            if status_code == STATUS_IDLEEXC:
                raise RuntimeError(f"daemon idle with exception: {reply['status']}")
            queued = {
                item.get("reqid")
                for item in reply.get("requests", [])
                if isinstance(item, dict)
            }
            if reqid not in queued and status_code == STATUS_IDLE:
                return reqid
            time.sleep(0.05)

        raise TimeoutError(f"timed out waiting for request completion: {reqid}")
        return reqid


SmokeAssertion = Callable[[SmokeClient], None]


def _compose_base_cmd() -> list[str]:
    for candidate in (["docker", "compose"], ["docker-compose"]):
        try:
            subprocess.run(
                candidate + ["version"],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return candidate
        except (OSError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("docker compose is required but was not found")


def _run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path = REPO_ROOT,
) -> subprocess.CompletedProcess:
    kwargs = {
        "cwd": cwd,
        "env": env,
        "text": True,
    }
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout or ''}\n"
            f"stderr:\n{result.stderr or ''}"
        )
    return result


def _compose(
    compose_base: list[str], *args: str, check: bool = True
) -> subprocess.CompletedProcess:
    return _run(
        compose_base + ["-f", str(COMPOSE_FILE)] + list(args),
        check=check,
        capture=True,
    )


def _ensure_runtime_dirs(clean: bool) -> None:
    if clean and RUNTIME_ROOT.exists():
        shutil.rmtree(RUNTIME_ROOT)

    for directory in (
        RUNTIME_ROOT,
        RUNTIME_ROOT / "pid",
        RUNTIME_ROOT / "log",
        RUNTIME_ROOT / "data",
        RUNTIME_ROOT / "keystore",
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _ensure_runtime_files(clean: bool) -> None:
    """
    Ensure any files expected by the smoke stack exist, creating or cleaning as needed.
        - cached_proposals.json: Used by the experiment device, should be a valid JSON object.
        - counters: Used by the file writer pool device, should be a text file with lines of the form `counter_name number`.
    """
    cached_proposals = RUNTIME_ROOT / "cached_proposals.json"
    if clean or not cached_proposals.exists():
        cached_proposals.write_text("{}", encoding="utf-8")

    counters_file = RUNTIME_ROOT / "counters"
    if clean or not counters_file.exists():
        counters_file.write_text("scan 1\nfile 1", encoding="utf-8")


def _wait_for_port(host: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"timed out waiting for {host}:{port}")


def _compose_diagnostics(compose_base: list[str]) -> str:
    ps = _compose(compose_base, "ps", "-a", check=False)
    logs = _compose(compose_base, "logs", "--no-color", "kafka", check=False)
    return (
        "docker compose diagnostics\n"
        f"ps:\n{ps.stdout or ps.stderr or '<no output>'}\n"
        f"logs:\n{logs.stdout or logs.stderr or '<no output>'}"
    )


def _wait_for_kafka_ready(compose_base: list[str], timeout: float = 120.0) -> None:
    _wait_for_port("localhost", 19092, timeout=timeout)

    deadline = time.monotonic() + timeout
    last_error = ""
    admin = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP})
    while time.monotonic() < deadline:
        try:
            metadata = admin.list_topics(timeout=5)
            if metadata and metadata.brokers:
                return
            last_error = "broker metadata available but empty"
        except KafkaException as exc:
            last_error = str(exc)
        time.sleep(1.0)
    diagnostics = _compose_diagnostics(compose_base)
    raise TimeoutError(
        "timed out waiting for Kafka broker readiness\n"
        f"last probe error:\n{last_error or '<none>'}\n\n{diagnostics}"
    )


def _ensure_topics(compose_base: list[str], topics: list[str]) -> None:
    admin = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP})
    futures = admin.create_topics(
        [NewTopic(topic, num_partitions=1, replication_factor=1) for topic in topics]
    )
    topic_failures = []
    for topic, future in futures.items():
        try:
            future.result(timeout=20)
        except KafkaException as exc:
            # Topic exists is fine for reruns.
            if "TOPIC_ALREADY_EXISTS" not in str(exc):
                topic_failures.append(f"{topic}: {exc}")
    if topic_failures:
        diagnostics = _compose_diagnostics(compose_base)
        failures = "\n".join(topic_failures)
        raise RuntimeError(
            f"failed to create Kafka topics:\n{failures}\n\n{diagnostics}"
        )


def _pva_to_float(value) -> float:
    try:
        return float(value["value"])
    except Exception:
        return float(value)


def _wait_for_pva_ready(pva_server: SmokePvaServer, timeout: float = 15.0) -> None:
    names = pva_server.names
    ctx = PvaContext("pva", nt=False)
    deadline = time.monotonic() + timeout
    last_error = ""
    probe_target = 0.25
    try:
        while time.monotonic() < deadline:
            try:
                _pva_to_float(ctx.get(names.readable, timeout=1.0))
                _pva_to_float(ctx.get(names.move_read, timeout=1.0))
                _pva_to_float(ctx.get(names.move_write, timeout=1.0))

                ctx.put(names.move_write, probe_target, wait=True, timeout=1.0)
                rbv_deadline = time.monotonic() + 3.0
                while time.monotonic() < rbv_deadline:
                    rbv = _pva_to_float(ctx.get(names.move_read, timeout=0.5))
                    if abs(rbv - probe_target) <= 1e-6:
                        return
                    time.sleep(0.05)
                last_error = "write acknowledged but readback did not update"
            except Exception as err:
                last_error = str(err)
            time.sleep(0.1)
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    raise TimeoutError(f"timed out waiting for PVA server readiness: {last_error}")


def _tail(path: Path, lines: int = 80) -> str:
    if not path.exists():
        return "<log file not found>"
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def _start_service(name: str, args: list[str], env: dict[str, str]) -> ManagedProcess:
    log_path = LOG_ROOT / f"{name}.log"
    handle = open(log_path, "w", encoding="utf-8")
    process = subprocess.Popen(
        args,
        cwd=REPO_ROOT,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    return ManagedProcess(name, process, handle, log_path)


def _stop_process(proc: ManagedProcess, timeout: float = 8.0) -> None:
    try:
        if proc.process.poll() is None:
            try:
                os.killpg(proc.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if proc.process.poll() is not None:
                    break
                time.sleep(0.1)
            else:
                try:
                    os.killpg(proc.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    finally:
        proc.logfile_handle.close()


def _smoke_assertions(client: SmokeClient) -> None:
    client.wait_idle(timeout=90)

    # Load device setup under the running daemon.
    client.eval("session.loadSetup('system')")
    client.wait_idle(timeout=60)

    expected = {
        "SmokeReadable",
        "SmokeMoveable",
        "FileWriterStatus",
        "FileWriterControl",
        "KafkaForwarder",
    }
    explicit_devices = set(client.eval("sorted(session.explicit_devices)"))
    missing = sorted(expected - explicit_devices)
    if missing:
        raise AssertionError(f"missing expected devices after setup load: {missing}")

    readable_value = client.eval("session.getDevice('SmokeReadable').read(0)")
    if abs(float(readable_value) - 1.23) > 1e-6:
        raise AssertionError(f"unexpected SmokeReadable value: {readable_value}")

    # Verify Kafka-backed status devices are reachable.
    client.eval("session.getDevice('FileWriterStatus').status(0)")
    client.eval("session.getDevice('KafkaForwarder').status(0)")

    # End-to-end move and wait over daemon/poller/cache/PVA stack.
    client.eval("session.getDevice('SmokeMoveable').maw(5.0)")
    moved = client.eval("session.getDevice('SmokeMoveable').read(0)")
    if abs(float(moved) - 5.0) > 0.05:
        raise AssertionError(f"SmokeMoveable did not reach target: {moved}")


@contextmanager
def smoke_client_session(
    *,
    keep_kafka: bool = False,
    clean_runtime: bool = True,
) -> Iterator[SmokeClient]:
    """Start the full smoke stack and yield a connected daemon client."""
    compose_base = _compose_base_cmd()
    _ensure_runtime_dirs(clean_runtime)
    _ensure_runtime_files(clean_runtime)

    pva_server = None
    managed: list[ManagedProcess] = []

    base_env = os.environ.copy()
    base_env["INSTRUMENT"] = "integration_test.smoke"
    base_env["PYTHONUNBUFFERED"] = "1"
    base_env["EPICS_CA_AUTO_ADDR_LIST"] = "NO"
    base_env["EPICS_CA_ADDR_LIST"] = "127.0.0.1"
    base_env["EPICS_PVA_AUTO_ADDR_LIST"] = "NO"
    base_env["EPICS_PVA_ADDR_LIST"] = "127.0.0.1"
    base_env["PYTHONPATH"] = (
        f"{REPO_ROOT}:{base_env['PYTHONPATH']}"
        if base_env.get("PYTHONPATH")
        else str(REPO_ROOT)
    )

    # Explicitly disable SASL options for local plain-text smoke Kafka.
    for key in (
        "KAFKA_SSL_PROTOCOL",
        "KAFKA_SSL_MECHANISM",
        "KAFKA_CERT_PATH",
        "KAFKA_USER",
    ):
        base_env.pop(key, None)

    client = SmokeClient()

    try:
        print("[smoke] starting Kafka (docker compose)", flush=True)
        _compose(compose_base, "up", "-d", "kafka", check=True)
        _wait_for_kafka_ready(compose_base)

        print("[smoke] creating Kafka topics", flush=True)
        _ensure_topics(compose_base, SMOKE_TOPICS)

        print("[smoke] starting local PVA server", flush=True)
        pva_server = SmokePvaServer()
        pva_server.start()
        _wait_for_pva_ready(pva_server)

        print("[smoke] starting nicos-cache", flush=True)
        cache = _start_service(
            "nicos-cache",
            [sys.executable, "bin/nicos-cache", "-S", "cache"],
            base_env,
        )
        managed.append(cache)
        _wait_for_port(CACHE_HOST, CACHE_PORT, timeout=30.0)

        print("[smoke] starting nicos-poller", flush=True)
        poller = _start_service(
            "nicos-poller",
            [sys.executable, "bin/nicos-poller", "-S", "poller"],
            base_env,
        )
        managed.append(poller)

        print("[smoke] starting nicos-collector", flush=True)
        collector = _start_service(
            "nicos-collector",
            [sys.executable, "bin/nicos-collector", "-S", "collector"],
            base_env,
        )
        managed.append(collector)

        print("[smoke] starting nicos-daemon", flush=True)
        daemon = _start_service(
            "nicos-daemon",
            [sys.executable, "bin/nicos-daemon", "-S", "daemon"],
            base_env,
        )
        managed.append(daemon)
        _wait_for_port(DAEMON_HOST, DAEMON_PORT, timeout=40.0)

        conn = parseConnectionString(f"user:user@{DAEMON_HOST}:{DAEMON_PORT}", 0)
        client.connect(ConnectionData(**conn))
        if not client.isconnected:
            raise RuntimeError("failed to establish daemon client connection")
        client.wait_idle(timeout=90)
        yield client

    except Exception:
        print("[smoke] FAILURE; dumping service log tails", flush=True)
        for proc in managed:
            print(f"\n--- {proc.name} ({proc.logfile_path}) ---")
            print(_tail(proc.logfile_path))
        raise
    finally:
        if client.isconnected:
            client._disconnecting = True
            client.disconnect()

        for proc in reversed(managed):
            _stop_process(proc)

        if pva_server is not None:
            pva_server.stop()

        if not keep_kafka:
            _compose(compose_base, "down", "-v", check=False)


def run_smoke(
    *,
    keep_kafka: bool = False,
    clean_runtime: bool = True,
    assertions: SmokeAssertion | None = None,
) -> None:
    smoke_assertions = assertions or _smoke_assertions
    with smoke_client_session(
        keep_kafka=keep_kafka, clean_runtime=clean_runtime
    ) as client:
        print("[smoke] running smoke assertions", flush=True)
        smoke_assertions(client)
        print("[smoke] SUCCESS", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-kafka",
        action="store_true",
        help="Do not bring down the kafka compose stack after the run",
    )
    parser.add_argument(
        "--no-clean-runtime",
        action="store_true",
        help="Keep previous runtime logs/data instead of cleaning first",
    )
    args = parser.parse_args()

    run_smoke(keep_kafka=args.keep_kafka, clean_runtime=not args.no_clean_runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

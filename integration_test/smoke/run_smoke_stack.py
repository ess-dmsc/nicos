#!/usr/bin/env python3
"""Run the NICOS-owned smoke stack.

Stack components:
- Kafka (docker compose)
- Filewriter Kafka double
- Local in-process PVA server
- nicos-cache
- nicos-poller
- nicos-collector
- nicos-daemon
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, TextIO

from confluent_kafka import OFFSET_END, Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
from p4p.client.thread import Context as PvaContext
from streaming_data_types import deserialise_x5f2

from integration_test.smoke.pva_server import SmokePvaServer
from nicos.clients.base import ConnectionData, NicosClient
from nicos.protocols.daemon import STATUS_IDLE, STATUS_IDLEEXC
from nicos.utils import parseConnectionString

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = SMOKE_ROOT / "docker-compose.yml"
ROOT_NICOS_CONF = REPO_ROOT / "nicos.conf"

SMOKE_SETUP_PACKAGE = "nicos_smoke_runtime"
SMOKE_INSTRUMENT = f"{SMOKE_SETUP_PACKAGE}.smoke"
DEFAULT_KAFKA_BOOTSTRAP = "localhost:19092"

SMOKE_FILEWRITER_INSTRUMENT_TOPIC = "test_smoke_filewriter"
SMOKE_FILEWRITER_STATUS_TOPIC = "test_smoke_filewriter_status"
SMOKE_FILEWRITER_POOL_TOPIC = "test_smoke_filewriter_pool"

SMOKE_TOPICS = [
    "test_smoke_forwarder_dynamic_status",
    "test_smoke_forwarder_dynamic_config",
    SMOKE_FILEWRITER_INSTRUMENT_TOPIC,
    SMOKE_FILEWRITER_STATUS_TOPIC,
    SMOKE_FILEWRITER_POOL_TOPIC,
    "test_smoke_scichat",
    "test_smoke_nicos_devices",
]


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen
    logfile_handle: TextIO
    logfile_path: Path


@dataclass(frozen=True)
class SmokeRuntime:
    root: Path
    log_root: Path
    cache_host: str
    cache_port: int
    daemon_host: str
    daemon_port: int
    artifact_root: Path | None


@dataclass(frozen=True)
class SmokeDevice:
    """Reference to a device variable in daemon script namespace."""

    name: str


class SmokeClient(NicosClient):
    """Daemon client with command-style helpers for smoke tests."""

    def __init__(self):
        self._disconnecting = False
        self._done_results = {}
        self._done_lock = threading.Lock()
        self._async_errors = []
        self._async_error_lock = threading.Lock()
        super().__init__(print)

    def signal(self, name, data=None, data2=None):
        if name == "error":
            self._record_async_error(f"daemon client error: {data} ({data2})")
        elif name == "broken":
            self._record_async_error(f"daemon connection broken: {data}")
        elif name == "disconnected" and not self._disconnecting:
            self._record_async_error("daemon disconnected unexpectedly")
        elif name == "done" and isinstance(data, dict) and "reqid" in data:
            with self._done_lock:
                self._done_results[data["reqid"]] = bool(data.get("success", False))

    def _record_async_error(self, message: str) -> None:
        with self._async_error_lock:
            self._async_errors.append(message)

    def _raise_async_error(self) -> None:
        with self._async_error_lock:
            errors = self._async_errors[:]
            self._async_errors.clear()
        if errors:
            raise RuntimeError("\n".join(errors))

    def dev(self, name: str) -> SmokeDevice:
        """Return a device reference for command calls (e.g. maw(dev('m'), 5))."""
        return SmokeDevice(name=name)

    def read(self, device: SmokeDevice | str, maxage=0):
        """Read a device value using direct device API in daemon namespace."""
        return self.eval(f"{self._device_expr(device)}.read({maxage!r})")

    def status(self, device: SmokeDevice | str, maxage=0):
        """Read a device status using direct device API in daemon namespace."""
        return self.eval(f"{self._device_expr(device)}.status({maxage!r})")

    def run_command(self, command_name: str, *args, timeout: float = 60.0, **kwargs):
        """Execute one NICOS command by name, for example `NewSetup(...)`."""
        rendered_args = [self._format_arg(arg) for arg in args]
        rendered_args.extend(
            f"{key}={self._format_arg(value)}" for key, value in kwargs.items()
        )
        source = f"{command_name}({', '.join(rendered_args)})"
        return self.execute(source, timeout=timeout)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _command(*args, timeout: float = 60.0, **kwargs):
            return self.run_command(name, *args, timeout=timeout, **kwargs)

        return _command

    def _format_arg(self, value) -> str:
        if isinstance(value, SmokeDevice):
            # Script execution namespace resolves device variables by name.
            return value.name
        return repr(value)

    def _device_expr(self, device: SmokeDevice | str) -> str:
        if isinstance(device, SmokeDevice):
            return f"session.getDevice({device.name!r})"
        if isinstance(device, str):
            return f"session.getDevice({device!r})"
        return f"session.getDevice({device!r})"

    def _consume_done_result(self, reqid: str):
        with self._done_lock:
            return self._done_results.pop(reqid, None)

    def _request_error_text(self, reqid: str) -> str:
        messages = self.ask("getmessages", "300", quiet=True, default=[]) or []
        related_errors = []
        for message in messages:
            if not isinstance(message, (list, tuple)) or len(message) < 6:
                continue
            logger_name, _timestamp, levelno, text, exc_text, message_reqid = message[
                :6
            ]
            if message_reqid != reqid or levelno < 40:
                continue
            prefix = f"{logger_name}: " if logger_name else ""
            related_errors.append(f"{prefix}{text}".strip())
            if exc_text:
                related_errors.append(str(exc_text).strip())
        return "\n".join(related_errors[-12:]).strip()

    def _raise_script_failure(self, reqid: str, code: str) -> None:
        req_errors = self._request_error_text(reqid)
        if req_errors:
            raise RuntimeError(
                f"script failed (reqid={reqid}) for code {code!r}\n{req_errors}"
            )
        trace = self.ask("gettrace", quiet=True, default="")
        if trace:
            raise RuntimeError(
                f"script failed (reqid={reqid}) for code {code!r}\n{trace}"
            )
        raise RuntimeError(f"script failed (reqid={reqid}) for code {code!r}")

    def wait_idle(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._raise_async_error()
            reply = self.ask("getstatus", quiet=True, default=None)
            if reply and reply["status"][0] in (STATUS_IDLE, STATUS_IDLEEXC):
                if reply["status"][0] == STATUS_IDLEEXC:
                    trace = self.ask("gettrace", quiet=True, default="")
                    if trace:
                        raise RuntimeError(
                            f"daemon idle with exception: {reply['status']}\n{trace}"
                        )
                    raise RuntimeError(f"daemon idle with exception: {reply['status']}")
                return
            time.sleep(0.1)
        raise TimeoutError("timed out waiting for daemon idle status")

    def execute(self, code: str, *, timeout: float = 60.0) -> str:
        """Execute command/script text and wait for this request to complete.

        Behavior matches CLI usage:
        - try immediate `start` first
        - if daemon is busy, fall back to queued execution
        """
        reqid = self.run(code, filename="<smoke-test>", noqueue=True)
        if reqid is None:
            reqid = self.run(code, filename="<smoke-test>", noqueue=False)
        if reqid is None:
            raise RuntimeError(f"failed to execute command: {code!r}")

        deadline = time.monotonic() + timeout
        saw_activity = False
        while time.monotonic() < deadline:
            self._raise_async_error()
            done_result = self._consume_done_result(reqid)
            if done_result is True:
                return reqid
            if done_result is False:
                self._raise_script_failure(reqid, code)
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
            if reqid in queued:
                saw_activity = True
            elif status_code not in (STATUS_IDLE, STATUS_IDLEEXC):
                # start(noqueue) may run before request list catches up.
                saw_activity = True

            if saw_activity and reqid not in queued:
                if status_code == STATUS_IDLE:
                    return reqid
                if status_code == STATUS_IDLEEXC:
                    self._raise_script_failure(reqid, code)
            time.sleep(0.05)

        raise TimeoutError(f"timed out waiting for request completion: {reqid}")


SmokeAssertion = Callable[[SmokeClient], None]


def _assert_no_root_nicos_conf() -> None:
    """Fail fast when repo-root nicos.conf could override smoke config.

    NICOS merges a repo-root nicos.conf over the instrument config. Any
    repo-root nicos.conf, symlink or regular file, invalidates this smoke run.
    """
    if not ROOT_NICOS_CONF.exists() and not ROOT_NICOS_CONF.is_symlink():
        return
    detail = ""
    if ROOT_NICOS_CONF.is_symlink():
        detail = f" ({ROOT_NICOS_CONF} -> {os.readlink(ROOT_NICOS_CONF)})"
    raise RuntimeError(
        "Smoke integration tests cannot run: "
        f"repo-root nicos.conf exists{detail}. "
        "It overrides the smoke configuration and leads to invalid test runs. "
        "Remove the repo-root nicos.conf and rerun."
    )


def _env_flag(name: str, *, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _kafka_bootstrap(default: str = DEFAULT_KAFKA_BOOTSTRAP) -> str:
    value = os.environ.get("NICOS_SMOKE_KAFKA_BOOTSTRAP", default)
    endpoints = [entry.strip() for entry in value.split(",") if entry.strip()]
    if not endpoints:
        return default
    return ",".join(endpoints)


def _first_bootstrap_endpoint(bootstrap_servers: str) -> tuple[str, int]:
    endpoint = bootstrap_servers.split(",", 1)[0].strip()
    host, port_str = endpoint.rsplit(":", 1)
    return host.strip(), int(port_str)


def _endpoint(host: str, port: int) -> str:
    return f"{host}:{port}"


def _split_endpoint(endpoint: str) -> tuple[str, int]:
    host, port_str = endpoint.rsplit(":", 1)
    return host.strip(), int(port_str)


def _free_tcp_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _runtime_root() -> Path:
    configured = os.environ.get("NICOS_SMOKE_RUNTIME_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.mkdtemp(prefix="nicos-smoke-")).resolve()


def _artifact_root() -> Path | None:
    configured = os.environ.get("NICOS_SMOKE_ARTIFACT_ROOT")
    if not configured:
        return None
    return Path(configured).expanduser().resolve()


def _safe_clean_runtime_root(runtime_root: Path) -> None:
    """Only delete directories that this smoke runner clearly owns."""
    marker = runtime_root / ".nicos-smoke-runtime"
    if not runtime_root.exists():
        return
    if marker.exists() or runtime_root.name.startswith("nicos-smoke-"):
        shutil.rmtree(runtime_root)
        return
    raise RuntimeError(
        "refusing to clean unmarked smoke runtime root: "
        f"{runtime_root}. Remove it manually or choose a nicos-smoke-* path."
    )


def _prepare_runtime_package(runtime_root: Path) -> None:
    package_root = runtime_root / SMOKE_SETUP_PACKAGE
    smoke_root = package_root / "smoke"
    setups_target = smoke_root / "setups"
    if setups_target.exists():
        shutil.rmtree(setups_target)
    shutil.copytree(
        SMOKE_ROOT / "setups",
        setups_target,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    smoke_root.mkdir(parents=True, exist_ok=True)
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (smoke_root / "__init__.py").write_text("", encoding="utf-8")
    (smoke_root / "nicos.conf").write_text(
        f"""
[nicos]
setup_package = {json.dumps(SMOKE_SETUP_PACKAGE)}
instrument = "smoke"
setup_subdirs = ["smoke"]
services = ["cache", "poller", "collector", "daemon"]
pid_path = {json.dumps(str(runtime_root / "pid"))}
logging_path = {json.dumps(str(runtime_root / "log"))}
keystorepaths = [{json.dumps(str(runtime_root / "keystore"))}]

[environment]
DEFAULT_EPICS_PROTOCOL = "pva"
EPICS_CA_AUTO_ADDR_LIST = "NO"
EPICS_CA_ADDR_LIST = "127.0.0.1"
EPICS_PVA_AUTO_ADDR_LIST = "NO"
EPICS_PVA_ADDR_LIST = "127.0.0.1"
KAFKA_SSL_PROTOCOL = ""
KAFKA_SSL_MECHANISM = ""
KAFKA_CERT_PATH = ""
KAFKA_USER = ""
""".lstrip(),
        encoding="utf-8",
    )


def _ensure_runtime_dirs(runtime_root: Path, clean: bool) -> None:
    if clean:
        _safe_clean_runtime_root(runtime_root)

    for directory in (
        runtime_root,
        runtime_root / "pid",
        runtime_root / "log",
        runtime_root / "data",
        runtime_root / "keystore",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    (runtime_root / ".nicos-smoke-runtime").write_text("", encoding="utf-8")


def _ensure_runtime_files(runtime_root: Path, clean: bool) -> None:
    cached_proposals = runtime_root / "cached_proposals.json"
    if clean or not cached_proposals.exists():
        cached_proposals.write_text("{}", encoding="utf-8")

    counters_file = runtime_root / "data" / "counters"
    if clean or not counters_file.exists():
        counters_file.write_text("scan 0\nfile 0", encoding="utf-8")


def _prepare_runtime(clean: bool) -> SmokeRuntime:
    runtime_root = _runtime_root()
    _ensure_runtime_dirs(runtime_root, clean)
    _ensure_runtime_files(runtime_root, clean)
    _prepare_runtime_package(runtime_root)

    cache_endpoint = os.environ.get(
        "NICOS_SMOKE_CACHE_HOST", _endpoint("127.0.0.1", _free_tcp_port())
    )
    daemon_endpoint = os.environ.get(
        "NICOS_SMOKE_DAEMON_HOST", _endpoint("127.0.0.1", _free_tcp_port())
    )
    cache_host, cache_port = _split_endpoint(cache_endpoint)
    daemon_host, daemon_port = _split_endpoint(daemon_endpoint)

    return SmokeRuntime(
        root=runtime_root,
        log_root=runtime_root / "log",
        cache_host=cache_host,
        cache_port=cache_port,
        daemon_host=daemon_host,
        daemon_port=daemon_port,
        artifact_root=_artifact_root(),
    )


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
    compose_base: list[str],
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    return _run(
        compose_base + ["-f", str(COMPOSE_FILE)] + list(args),
        check=check,
        capture=True,
        env=env,
    )


def _wait_for_port(host: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"timed out waiting for {host}:{port}")


def _compose_diagnostics(compose_base: list[str], env: dict[str, str]) -> str:
    ps = _compose(compose_base, "ps", "-a", check=False, env=env)
    logs = _compose(compose_base, "logs", "--no-color", "kafka", check=False, env=env)
    return (
        "docker compose diagnostics\n"
        f"ps:\n{ps.stdout or ps.stderr or '<no output>'}\n"
        f"logs:\n{logs.stdout or logs.stderr or '<no output>'}"
    )


def _wait_for_kafka_ready(
    bootstrap_servers: str,
    *,
    timeout: float = 120.0,
    compose_base: list[str] | None = None,
    compose_env: dict[str, str] | None = None,
) -> None:
    host, port = _first_bootstrap_endpoint(bootstrap_servers)
    _wait_for_port(host, port, timeout=timeout)

    deadline = time.monotonic() + timeout
    last_error = ""
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    while time.monotonic() < deadline:
        try:
            metadata = admin.list_topics(timeout=5)
            if metadata and metadata.brokers:
                return
            last_error = "broker metadata available but empty"
        except KafkaException as exc:
            last_error = str(exc)
        time.sleep(1.0)
    diagnostics = (
        _compose_diagnostics(compose_base, compose_env or os.environ.copy())
        if compose_base is not None
        else "<none>"
    )
    raise TimeoutError(
        "timed out waiting for Kafka broker readiness\n"
        f"last probe error:\n{last_error or '<none>'}\n\n{diagnostics}"
    )


def _ensure_topics(
    bootstrap_servers: str,
    topics: list[str],
    compose_base: list[str] | None = None,
    compose_env: dict[str, str] | None = None,
) -> None:
    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
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
        diagnostics = (
            _compose_diagnostics(compose_base, compose_env or os.environ.copy())
            if compose_base is not None
            else "<none>"
        )
        failures = "\n".join(topic_failures)
        raise RuntimeError(
            f"failed to create Kafka topics:\n{failures}\n\n{diagnostics}"
        )


def _wait_for_filewriter_double_ready(
    proc: ManagedProcess,
    bootstrap_servers: str,
    status_topic: str,
    timeout: float = 20.0,
) -> None:
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": (
                f"nicos-smoke-filewriter-ready-{os.getpid()}-{int(time.time() * 1000)}"
            ),
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
            "allow.auto.create.topics": False,
        }
    )
    try:
        metadata = consumer.list_topics(status_topic, timeout=5)
        topic = metadata.topics.get(status_topic)
        if topic is None:
            raise RuntimeError(f"Kafka topic does not exist: {status_topic}")
        partitions = [
            TopicPartition(status_topic, partition_id, OFFSET_END)
            for partition_id in topic.partitions
        ]
        consumer.assign(partitions)

        deadline = time.monotonic() + timeout
        last_error = ""
        while time.monotonic() < deadline:
            _assert_process_running(proc)
            msg = consumer.poll(0.5)
            if msg is None:
                continue
            if msg.error():
                last_error = str(msg.error())
                continue
            value = msg.value()
            if len(value) < 8 or value[4:8] != b"x5f2":
                continue
            status_info = json.loads(deserialise_x5f2(value).status_json)
            if status_info.get("state") == "idle":
                return
            last_error = f"last filewriter state was {status_info!r}"
    finally:
        consumer.close()

    raise TimeoutError(
        "timed out waiting for filewriter double idle status "
        f"on {status_topic}: {last_error or '<no status>'}\n"
        f"{_tail(proc.logfile_path)}"
    )


def _pva_to_float(value) -> float:
    try:
        return float(value["value"])
    except Exception:
        return float(value)


def _wait_for_pva_ready(pva_server: SmokePvaServer, timeout: float = 15.0) -> None:
    """Read PVs only; readiness must not move the simulated device."""
    names = pva_server.names
    ctx = PvaContext("pva", nt=False)
    deadline = time.monotonic() + timeout
    last_error = ""
    try:
        while time.monotonic() < deadline:
            try:
                _pva_to_float(ctx.get(names.readable, timeout=1.0))
                _pva_to_float(ctx.get(names.move_read, timeout=1.0))
                _pva_to_float(ctx.get(names.move_write, timeout=1.0))
                return
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


def _start_service(
    name: str, args: list[str], env: dict[str, str], log_root: Path
) -> ManagedProcess:
    log_path = log_root / f"{name}.log"
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


def _assert_process_running(proc: ManagedProcess) -> None:
    exit_code = proc.process.poll()
    if exit_code is None:
        return
    raise RuntimeError(
        f"{proc.name} exited during startup with code {exit_code}\n"
        f"{_tail(proc.logfile_path)}"
    )


def _wait_for_process_port(
    proc: ManagedProcess, host: str, port: int, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _assert_process_running(proc)
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(
        f"timed out waiting for {proc.name} on {host}:{port}\n"
        f"{_tail(proc.logfile_path)}"
    )


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


def _copy_runtime_artifacts(runtime: SmokeRuntime) -> None:
    if runtime.artifact_root is None:
        return
    runtime.artifact_root.mkdir(parents=True, exist_ok=True)
    for name in ("log", "data", "cached_proposals.json"):
        source = runtime.root / name
        target = runtime.artifact_root / name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        elif source.exists():
            shutil.copy2(source, target)


def _smoke_assertions(client: SmokeClient) -> None:
    from integration_test.smoke.test_smoke import (
        test_full_experiment_workflow_with_filewriter_scan,
    )

    test_full_experiment_workflow_with_filewriter_scan(client)


def _compose_project_name(runtime_root: Path) -> str:
    suffix = "".join(
        char if char.isalnum() else "-" for char in runtime_root.name.lower()
    ).strip("-")
    return f"nicos-smoke-{suffix or 'run'}"


def _compose_env(runtime_root: Path, kafka_bootstrap: str) -> dict[str, str]:
    host, port = _first_bootstrap_endpoint(kafka_bootstrap)
    bind_host = "127.0.0.1" if host == "localhost" else host
    env = os.environ.copy()
    # Isolate compose resources so parallel smoke runs do not share containers.
    env["COMPOSE_PROJECT_NAME"] = _compose_project_name(runtime_root)
    env["NICOS_SMOKE_KAFKA_BIND"] = bind_host
    env["NICOS_SMOKE_KAFKA_HOST_PORT"] = str(port)
    env["NICOS_SMOKE_KAFKA_ADVERTISED_HOST"] = host
    env["NICOS_SMOKE_KAFKA_ADVERTISED_PORT"] = str(port)
    return env


@contextmanager
def smoke_client_session(
    *,
    keep_kafka: bool = False,
    clean_runtime: bool = True,
) -> Iterator[SmokeClient]:
    """Start the full smoke stack and yield a connected daemon client."""
    _assert_no_root_nicos_conf()
    manage_kafka = _env_flag("NICOS_SMOKE_MANAGE_KAFKA", default=True)
    kafka_default = (
        _endpoint("127.0.0.1", _free_tcp_port())
        if manage_kafka
        else DEFAULT_KAFKA_BOOTSTRAP
    )
    kafka_bootstrap = _kafka_bootstrap(kafka_default)
    compose_base = _compose_base_cmd() if manage_kafka else None
    runtime = _prepare_runtime(clean_runtime)
    compose_env = _compose_env(runtime.root, kafka_bootstrap) if manage_kafka else None

    pva_server = None
    managed: list[ManagedProcess] = []

    base_env = os.environ.copy()
    base_env["INSTRUMENT"] = SMOKE_INSTRUMENT
    base_env["PYTHONUNBUFFERED"] = "1"
    base_env["EPICS_CA_AUTO_ADDR_LIST"] = "NO"
    base_env["EPICS_CA_ADDR_LIST"] = "127.0.0.1"
    base_env["EPICS_PVA_AUTO_ADDR_LIST"] = "NO"
    base_env["EPICS_PVA_ADDR_LIST"] = "127.0.0.1"
    base_env["NICOS_SMOKE_RUNTIME_ROOT"] = str(runtime.root)
    base_env["NICOS_SMOKE_CACHE_HOST"] = _endpoint(
        runtime.cache_host, runtime.cache_port
    )
    base_env["NICOS_SMOKE_DAEMON_HOST"] = _endpoint(
        runtime.daemon_host, runtime.daemon_port
    )
    base_env["NICOS_SMOKE_KAFKA_BOOTSTRAP"] = kafka_bootstrap
    base_env["NICOS_SMOKE_FILEWRITER_POOL_TOPIC"] = SMOKE_FILEWRITER_POOL_TOPIC
    base_env["NICOS_SMOKE_FILEWRITER_STATUS_TOPIC"] = SMOKE_FILEWRITER_STATUS_TOPIC
    base_env["NICOS_SMOKE_FILEWRITER_INSTRUMENT_TOPIC"] = (
        SMOKE_FILEWRITER_INSTRUMENT_TOPIC
    )
    base_env["PYTHONPATH"] = (
        f"{runtime.root}:{REPO_ROOT}:{base_env['PYTHONPATH']}"
        if base_env.get("PYTHONPATH")
        else f"{runtime.root}:{REPO_ROOT}"
    )

    client = SmokeClient()
    client.runtime_root = runtime.root

    try:
        print(f"[smoke] runtime root: {runtime.root}", flush=True)
        if manage_kafka:
            assert compose_base is not None
            print("[smoke] starting Kafka (docker compose)", flush=True)
            assert compose_env is not None
            _compose(compose_base, "up", "-d", "kafka", check=True, env=compose_env)
            _wait_for_kafka_ready(
                kafka_bootstrap,
                compose_base=compose_base,
                compose_env=compose_env,
            )
        else:
            print(
                f"[smoke] using externally managed Kafka at {kafka_bootstrap}",
                flush=True,
            )
            _wait_for_kafka_ready(kafka_bootstrap)

        print("[smoke] creating Kafka topics", flush=True)
        _ensure_topics(
            kafka_bootstrap,
            SMOKE_TOPICS,
            compose_base=compose_base,
            compose_env=compose_env,
        )

        print("[smoke] starting filewriter double", flush=True)
        filewriter = _start_service(
            "filewriter-double",
            [
                sys.executable,
                "-m",
                "integration_test.doubles.filewriter",
                "--bootstrap",
                kafka_bootstrap,
                "--pool-topic",
                SMOKE_FILEWRITER_POOL_TOPIC,
                "--status-topic",
                SMOKE_FILEWRITER_STATUS_TOPIC,
            ],
            base_env,
            runtime.log_root,
        )
        managed.append(filewriter)
        _wait_for_filewriter_double_ready(
            filewriter,
            kafka_bootstrap,
            SMOKE_FILEWRITER_STATUS_TOPIC,
        )

        print("[smoke] starting local PVA server", flush=True)
        pva_server = SmokePvaServer()
        pva_server.start()
        _wait_for_pva_ready(pva_server)

        print("[smoke] starting nicos-cache", flush=True)
        cache = _start_service(
            "nicos-cache",
            [sys.executable, "bin/nicos-cache", "-S", "cache"],
            base_env,
            runtime.log_root,
        )
        managed.append(cache)
        _wait_for_process_port(
            cache, runtime.cache_host, runtime.cache_port, timeout=30.0
        )

        print("[smoke] starting nicos-poller", flush=True)
        poller = _start_service(
            "nicos-poller",
            [sys.executable, "bin/nicos-poller", "-S", "poller"],
            base_env,
            runtime.log_root,
        )
        managed.append(poller)
        time.sleep(0.5)
        _assert_process_running(poller)

        print("[smoke] starting nicos-collector", flush=True)
        collector = _start_service(
            "nicos-collector",
            [sys.executable, "bin/nicos-collector", "-S", "collector"],
            base_env,
            runtime.log_root,
        )
        managed.append(collector)
        time.sleep(0.5)
        _assert_process_running(collector)

        print("[smoke] starting nicos-daemon", flush=True)
        daemon = _start_service(
            "nicos-daemon",
            [sys.executable, "bin/nicos-daemon", "-S", "daemon"],
            base_env,
            runtime.log_root,
        )
        managed.append(daemon)
        _wait_for_process_port(
            daemon, runtime.daemon_host, runtime.daemon_port, timeout=40.0
        )

        conn = parseConnectionString(
            f"user:user@{runtime.daemon_host}:{runtime.daemon_port}", 0
        )
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

        _copy_runtime_artifacts(runtime)

        if manage_kafka and not keep_kafka:
            assert compose_base is not None
            assert compose_env is not None
            _compose(compose_base, "down", "-v", check=False, env=compose_env)


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

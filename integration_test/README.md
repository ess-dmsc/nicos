# NICOS Integration Smoke Stack

This directory contains the smoke integration path for NICOS-owned behavior:
daemon startup, setup/session commands, EPICS PVA device interaction, scans,
Kafka filewriter control, and local NICOS side effects.

It does not run the real downstream ESS stack. The real `kafka-to-nexus`
filewriter is replaced by a minimal Kafka filewriter double that speaks the
same control/status message types needed by NICOS. The double does not create
HDF/NeXus files.

## Startup Order

`smoke/run_smoke_stack.py` starts the stack in this order:

1. Kafka, via Docker Compose unless an external broker is requested.
2. All smoke Kafka topics.
3. The Kafka filewriter double.
4. A readiness check for an idle `x5f2` status from the filewriter double.
5. A local in-process EPICS PVA server.
6. `nicos-cache`.
7. `nicos-poller`.
8. `nicos-collector`.
9. `nicos-daemon`.
10. A `SmokeClient` connected to the daemon.

On failure, the runner prints service log tails. On teardown it stops all local
processes and removes the managed Kafka compose project unless `--keep-kafka`
is used.

## Files

- `smoke/test_smoke.py`: the actual pytest smoke workflow and assertions.
- `smoke/helpers.py`: polling and daemon-script helpers used by the test.
- `smoke/run_smoke_stack.py`: process orchestrator and `python -m` entry point.
- `smoke/conftest.py`: pytest fixture that gates the real smoke run behind
  `NICOS_RUN_SMOKE_INTEGRATION=1`.
- `smoke/docker-compose.yml`: Kafka plus the CI-only test container.
- `smoke/Dockerfile`: Python 3.13 `uv` image used by the CI-only container.
- `smoke/pva_server.py`: in-process PVA server for smoke PVs.
- `smoke/setups/`: smoke-owned NICOS setups copied into the runtime package.
- `smoke/nexus/smoke_nexus.json`: minimal smoke-owned NeXus structure.
- `doubles/filewriter.py`: standalone Kafka filewriter double.

There is no checked-in `smoke/nicos.conf`. The runner generates one under the
runtime root for each run and fails fast if a repo-root `nicos.conf` exists,
because that would override the smoke configuration.

## Filewriter Double

The runner owns these filewriter topics:

- `test_smoke_filewriter_pool`: shared start-job pool topic.
- `test_smoke_filewriter_status`: idle/default status topic.
- `test_smoke_filewriter`: instrument/control topic for the active job.

The double starts on the pool topic and publishes idle `x5f2` status to the
status topic. When it consumes a `pl72` start job it switches to the job control
topic, echoes the start message, publishes a successful `answ`, and emits
`x5f2` writing status. When it consumes a `6s4t` stop command it publishes a
successful stop `answ`, keeps reporting for a short stop leeway, publishes
`wrdn`, then returns to the pool topic and idle status.

The smoke test verifies that NICOS sees this lifecycle through
`FileWriterStatus`: no jobs initially, `STARTED` during `nexusfile_open`, and
`WRITTEN` after the stop leeway. It also runs `list_filewriting_jobs()` so the
command path is exercised.

## Test Coverage

`smoke/test_smoke.py` currently validates:

- loading the smoke `system`, `epics_basic`, and `detector` setups;
- EPICS PVA readable/moveable status and readback;
- `NewExperiment`, `NewSample`, and `SetDetectors`;
- `nexusfile_open` around a scan;
- filewriter active-job state and `FileWriterStatus` history;
- scan/file counter increments;
- experiment `lastscan` and current run number.

## Prerequisites

From the repository root:

```bash
uv sync --all-packages
```

Docker is required when the runner manages Kafka. CI uses Docker-in-Docker and
the same compose file as local runs.

## Run Locally

Run the stack through the module entry point:

```bash
uv run python -m integration_test.smoke.run_smoke_stack
```

Run the pytest smoke test directly:

```bash
NICOS_RUN_SMOKE_INTEGRATION=1 \
uv run pytest -q integration_test/smoke/test_smoke.py
```

Run pytest against an externally managed Kafka broker:

```bash
NICOS_RUN_SMOKE_INTEGRATION=1 \
NICOS_SMOKE_MANAGE_KAFKA=0 \
NICOS_SMOKE_KAFKA_BOOTSTRAP=kafka:9092 \
uv run pytest -q integration_test/smoke/test_smoke.py
```

Useful runner flags:

- `--keep-kafka`: leave the managed compose Kafka stack running after the run.
- `--no-clean-runtime`: reuse the configured runtime root instead of cleaning
  it first.

## Runtime State

Each run creates a per-run runtime directory under the system temp directory by
default. Set `NICOS_SMOKE_RUNTIME_ROOT=/path/to/runtime` to choose a specific
runtime root. Logs, counters, keystore files, copied setups, and the generated
`nicos.conf` live there.

Set `NICOS_SMOKE_ARTIFACT_ROOT=/path/to/artifacts` to copy runtime diagnostics
after teardown. CI uses this to publish `smoke-junit.xml`, service logs, Docker
build logs, compose logs, and compose state.

## Configuration

Common environment variables:

- `NICOS_SMOKE_MANAGE_KAFKA`: defaults to true. Set to `0` for external Kafka.
- `NICOS_SMOKE_KAFKA_BOOTSTRAP`: bootstrap servers for external Kafka, or an
  override for the managed Kafka host port.
- `NICOS_SMOKE_RUNTIME_ROOT`: optional runtime directory.
- `NICOS_SMOKE_ARTIFACT_ROOT`: optional artifact copy destination.
- `NICOS_SMOKE_CACHE_HOST`: optional `host:port` override for `nicos-cache`.
- `NICOS_SMOKE_DAEMON_HOST`: optional `host:port` override for `nicos-daemon`.

The runner sets the smoke filewriter topic environment variables for the NICOS
setups and the double. They are runner-owned details unless the harness itself
is being extended:

- `NICOS_SMOKE_FILEWRITER_POOL_TOPIC`
- `NICOS_SMOKE_FILEWRITER_STATUS_TOPIC`
- `NICOS_SMOKE_FILEWRITER_INSTRUMENT_TOPIC`

## Orchestration Model

The Python runner owns NICOS process orchestration and readiness checks. Compose
owns Kafka for local runs and provides the CI-only test container. Local Kafka
uses a per-run compose project and a dynamically allocated host port so separate
checkouts and repeated runs do not share the same Kafka container or port.

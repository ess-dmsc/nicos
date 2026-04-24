# NICOS Integration Smoke Stack

This smoke path validates NICOS-owned behavior with smoke-owned fixtures:
daemon startup, setup/session commands, EPICS PVA device interaction, scans,
and local NICOS side effects. It does not deploy or validate the downstream
ESS stack.

The runner starts:

- Kafka, via Docker Compose unless an external broker is requested
- a local in-process PVA server
- `nicos-cache`
- `nicos-poller`
- `nicos-collector`
- `nicos-daemon`

## Files

- `smoke/docker-compose.yml`: Kafka plus the CI-only smoke test container
- `smoke/Dockerfile`: Python 3.13 `uv` image used by CI
- `smoke/run_smoke_stack.py`: local NICOS process orchestrator
- `smoke/pva_server.py`: in-process PVA server for smoke PVs
- `smoke/setups/`: smoke-owned NICOS setups
- `smoke/nexus/smoke_nexus.json`: minimal smoke-owned NeXus structure

## Prerequisites

From the repository root:

```bash
uv sync --all-packages
```

Docker is required when the runner manages Kafka. CI uses Docker-in-Docker and
the same compose file as local runs.

## Run Locally

Use module execution so the smoke package is imported normally:

```bash
NICOS_RUN_SMOKE_INTEGRATION=1 \
uv run python -m integration_test.smoke.run_smoke_stack
```

Run the pytest smoke test directly:

```bash
NICOS_RUN_SMOKE_INTEGRATION=1 \
uv run pytest -q integration_test/smoke/test_smoke.py
```

Run against an externally managed Kafka broker:

```bash
NICOS_RUN_SMOKE_INTEGRATION=1 \
NICOS_SMOKE_MANAGE_KAFKA=0 \
NICOS_SMOKE_KAFKA_BOOTSTRAP=kafka:9092 \
uv run pytest -q integration_test/smoke/test_smoke.py
```

## Runtime State

Each run creates a per-run runtime directory under the system temp directory by
default. Set `NICOS_SMOKE_RUNTIME_ROOT=/path/to/runtime` to choose a specific
runtime root. Logs, counters, keystore files, and the generated smoke
`nicos.conf` live there.

Set `NICOS_SMOKE_ARTIFACT_ROOT=/path/to/artifacts` to copy runtime diagnostics
after teardown. CI uses this to publish `smoke-junit.xml`, service logs, Docker
build logs, compose logs, and compose state.

## Orchestration Model

The Python runner owns NICOS process orchestration. Compose owns Kafka for local
runs and provides the CI test container for Docker-in-Docker. Local Kafka uses a
per-run compose project and a dynamically allocated host port so separate
checkouts and repeated runs do not share the same Kafka container or port.

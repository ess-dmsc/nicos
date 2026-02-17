# NICOS Integration Smoke Stack

This folder contains an end-to-end smoke setup that starts a full NICOS stack:

- `nicos-cache`
- `nicos-poller`
- `nicos-collector`
- `nicos-daemon`
- Kafka (docker compose)
- local PVA server

The smoke setup includes ESS EPICS devices from
`nicos_ess/devices/epics/pva/epics_devices.py` plus Kafka/filewriter devices
(`KafkaForwarder`, `FileWriterStatus`, `FileWriterControl`, `SciChat`).

All Kafka topics are prefixed with `test_smoke_`.

## Files

- `smoke/nicos.conf`: instrument config for `integration_test.smoke`
- `smoke/setups/special/*.py`: service setups (`cache`, `poller`, `collector`, `daemon`)
- `smoke/setups/system.py`: loaded by daemon during smoke checks
- `smoke/pva_server.py`: in-process PVA server for EPICS PVs
- `smoke/docker-compose.kafka.yml`: single-node KRaft Kafka for smoke runs
- `smoke/run_smoke_stack.py`: orchestrator script

## Startup Order

The runner enforces this order:

1. Start Kafka and wait for broker readiness
2. Create required Kafka topics
3. Start local PVA server
4. Start `nicos-cache` and wait until cache port is bound
5. Start `nicos-poller`
6. Start `nicos-collector`
7. Start `nicos-daemon`
8. Connect to daemon and run smoke assertions

## Run

From repository root:

```bash
python integration_test/smoke/run_smoke_stack.py
```

Useful options:

```bash
# keep Kafka container running after smoke
python integration_test/smoke/run_smoke_stack.py --keep-kafka

# keep previous runtime logs/data in integration_test/runtime/
python integration_test/smoke/run_smoke_stack.py --no-clean-runtime
```

## Pytest Smoke Fixture

Smoke tests can use a fixture that yields a connected daemon client and tears
down the full stack automatically after `yield`:

- fixture: `smoke_client` (module scope)
- location: `integration_test/smoke/conftest.py`
- native command-style calls via client methods:
  - `smoke_client.NewSetup(...)`
  - `smoke_client.maw(...)`
  - `smoke_client.count(...)`
  - `smoke_client.read(...)` and `smoke_client.status(...)`
  - `smoke_client.dev("DeviceName")` for script-style device references

Run the EPICS basic smoke tests with:

```bash
NICOS_RUN_SMOKE_INTEGRATION=1 pytest -q integration_test/smoke/test_smoke.py
```

## Notes

- The runner disables SASL env settings so local plain-text Kafka works even if
  your shell has production Kafka vars configured.
- Runtime logs are written to `integration_test/runtime/log/`.

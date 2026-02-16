# ESS Device Test Harness

This folder contains unit-style harness tests for ESS NICOS devices.

The harness gives you deterministic tests for daemon and poller behavior without
starting real NICOS daemon/poller processes, Redis, or EPICS IOCs.

## Fixtures

Fixtures are defined in `test/nicos_ess/conftest.py`.

- `device_harness`: default dual-session harness (daemon + poller) with shared cache.
- `daemon_device_harness`: single-session daemon-style harness.

## Which Fixture To Use

- Use `daemon_device_harness` for devices that only need local daemon logic.
- Use `device_harness` for devices where poller callbacks and daemon logic interact.
- Use `device_harness` for race-condition tests (callback timing, stale cache windows, `maw` behavior).

## Core Concepts

`device_harness` simulates two NICOS roles that share one in-memory cache:

- daemon role (`sessiontype=MAIN`)
- poller role (`sessiontype=POLLER`)

This is the key behavior needed for testing device code that depends on:

- cache values written by poller callbacks
- daemon status/read logic that consumes those values
- ordering/race windows between `start()`, callback updates, and completion checks

## Dual-Session Usage (`device_harness`)

### Create role-specific device copies

```python
def test_daemon_and_poller_copies(device_harness):
    daemon = device_harness.create("daemon", MyDevice, name="dev", readpv="SIM:READ")
    poller = device_harness.create("poller", MyDevice, name="dev", readpv="SIM:READ")

    device_harness.run("poller", poller._cache.put, poller._name, "moving", True)
    assert device_harness.run("daemon", daemon._cache.get, daemon, "moving") is True
```

### Use convenience helpers

```python
def test_with_helpers(device_harness):
    daemon, poller = device_harness.create_pair(
        MyMoveable,
        name="axis",
        shared={"transport": transport},
    )

    device_harness.run_poller(poller._cache.put, poller._name, "value", 12.0)
    value = device_harness.run_daemon(daemon.read, 0)
    assert value == 12.0
```

Useful methods on `device_harness`:

- `create(role, devcls, ...)`
- `create_daemon(devcls, ...)`
- `create_poller(devcls, ...)`
- `create_pair(devcls, name=..., shared=..., daemon=..., poller=...)`
- `run(role, func, *args, **kwargs)`
- `run_daemon(func, *args, **kwargs)`
- `run_poller(func, *args, **kwargs)`

## Single-Session Usage (`daemon_device_harness`)

Use this for straightforward daemon logic where no poller copy is needed.

```python
def test_daemon_only_logic(daemon_device_harness):
    dev = daemon_device_harness.create_master(MyDaemonOnlyDevice, name="dev")
    assert dev.read() == 0
```

Useful methods on `daemon_device_harness`:

- `create(devcls, ...)`
- `create_master(devcls, ...)`
- `create_sim(devcls, ...)`

## Testing Cache Age / `maxage`

`InMemoryCache.put_aged(...)` makes stale-entry tests readable:

```python
def test_maxage_behavior(device_harness):
    daemon = device_harness.create_daemon(MyReadable, name="dev", readpv="SIM:READ")
    device_harness.run_daemon(
        daemon._cache.put_aged,
        daemon,
        "value",
        10.0,
        age_seconds=30,
    )
    # assert device reads direct backend when maxage is stricter than cache age
```

## Reusable Doubles

Put test doubles in `test/nicos_ess/test_devices/doubles/` so multiple test modules
can share them.

Examples in this repository:

- `epics_pva_backend.py`
- `mapped_controller_devices.py`

## Contract / Drift Protection

`test_device_harness_contract.py` protects harness correctness by checking method
signatures against NICOS core types:

- `InMemoryCache` vs `nicos.devices.cacheclient.CacheClient`
- `UnitTestSession` vs `nicos.core.sessions.Session`

If NICOS session/cache APIs change, these tests fail and force harness updates.

`test_epics_pva_backend_contract.py` protects the EPICS fake backend contract:

- verifies `FakeEpicsBackend` method signatures against both production wrapper
  source files (`p4p.py` and `caproto.py`)
- verifies callback argument shape and default behavior used by EPICS devices

## Typical Test Structure

For readability, prefer Arrange/Act/Assert style:

- Setup
- Act
- Assert

Use explicit test names describing behavior, not implementation detail.

## Running The Harness Tests

Use the project environment:

```bash
conda run -n nicos-qt5 pytest -q test/nicos_ess/test_devices/test_device_harness_contract.py
conda run -n nicos-qt5 pytest -q test/nicos_ess/test_devices/test_epics_devices_harness.py
conda run -n nicos-qt5 pytest -q test/nicos_ess/test_devices/test_mapped_controller_harness.py
```

Or run ESS tests broadly:

```bash
conda run -n nicos-qt5 pytest -q test/nicos_ess
```

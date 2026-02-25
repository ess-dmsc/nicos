# ESS Testing Guide

This document explains how to test ESS NICOS code and when to use each test
style:

- pure unit tests
- harness-based device tests
- full fixture/setup tests
- smoke/integration tests

The goal is to keep tests fast and reliable while still covering real NICOS
behavior where it matters.

## Why Multiple Test Styles

NICOS device code sits between:

- NICOS session/cache/daemon/poller behavior
- facility setup wiring (`loadSetup`, attached devices, aliases)
- external systems (EPICS, Kafka, filewriter, network)

No single test style gives strong coverage across all three without tradeoffs.
Use the smallest style that can validate the behavior you care about.

## Device Test Minimum Checklist

For each device class, cover at least:

- construction/default parameters
- validation and error behavior
- read/status behavior for fresh and stale paths (`maxage`)
- move behavior and completion semantics (for moveables)
- poller callback behavior (where applicable)
- daemon/poller interaction for race-sensitive logic (where applicable)

For critical moveables, include:

- completion uses fresh readback when required
- stale cache does not produce false completion
- move-and-wait relevant timing paths

## Test Layers

### 1. Pure Unit Tests (No NICOS Session)

Use for core business logic that does not require NICOS device lifecycle.

Good fit:

- mapping/transform logic
- message parsing and filtering
- retry/backoff decision logic
- state-machine transitions that can be expressed as plain Python

Why:

- fastest tests
- least flaky
- easiest to reason about failures

Example scenario:

- implement payload-to-topic selection in a plain function/class
- test that logic directly with representative payload variants
- keep device tests focused on NICOS wrapper wiring (backend calls, cache/status
  side effects)

### 2. Harness-Based Device Tests

Recommended default for testing device behavior.

Use `test/nicos_ess/device_harness.py` fixtures from
`test/nicos_ess/conftest.py`:

- `daemon_device_harness`: single-session daemon-style tests
- `device_harness`: dual-session daemon+poller tests with shared in-memory cache

Harnesses include:

- lightweight in-memory session/cache behavior
- explicit daemon/poller role switching
- deterministic callback triggering and cache inspection

Harnesses do not include:

- setup loading via `session.loadSetup(...)`
- setup-file import/alias wiring behavior
- external processes or real network services

Good fit:

- per-device read/status/move behavior
- maxage/cache freshness behavior
- poller callback to cache write behavior
- daemon/poller race windows (`start`, completion, cache updates)
- behavior where `sessiontype` (`MAIN` vs `POLLER`) changes code path

Why:

- much faster and more deterministic than full setup tests
- explicitly supports daemon and poller role interaction
- no external process or network dependency

### 3. Full Fixture/Setup Tests

Session fixture style (`test/conftest.py` global `session` fixture).

Use the global `session` fixture (`test/conftest.py`) and setup loading via
`session.loadSetup(...)` as seen in tests like `test_forwarder.py`.

Good fit:

- verifying real setup wiring and attached device chains
- setup import/load behavior
- configuration-level behavior that depends on setup files
- compatibility checks for long-standing setup conventions

Why:

- closer to real NICOS session/setup behavior
- catches integration issues that harness tests intentionally simplify

Limitations:

- stateful
- more boilerplate code
- slower to execute
- harder to debug
- timing-sensitive behaviors can result in rare failure modes

### 4. Smoke/Integration Tests (Full Stack)

Use when validating end-to-end behavior across real services/processes:

- cache + poller + collector + daemon
- Kafka broker and topics
- EPICS PVA server

Good fit:

- startup/order assumptions
- cross-process communication
- environment and deployment parity checks

These are high-value but should be a small, focused set because they are the
most expensive and the most failure-prone.

## Decision Rule For New Tests

Start at the lowest layer that can prove the requirement:

1. If logic can be isolated from NICOS device classes, write pure unit tests.
2. If behavior depends on device lifecycle/sessiontype/cache callbacks, write
   harness tests.
3. If behavior depends on setup loading/attach chains/config wiring, add full
   fixture/setup tests.
4. If behavior depends on real processes/network startup order, add smoke tests.

Smoke tests are optional. Add them only when real process/network behavior is a
requirement for confidence.

Use higher layers only to test against components not present on lower layers.

## Recommended Split For New Device Work

For most new ESS device behavior:

- mostly pure unit tests for isolated logic
- then harness tests for NICOS device behavior
- then a small number of full fixture/setup checks when setup wiring matters
- then smoke/integration tests only for critical end-to-end production risks

As a practical rule, prefer writing most tests in unit+harness layers and keep
full-stack tests targeted.

## Harness Guidance

### Use `daemon_device_harness` when:

- only daemon-side behavior matters
- no poller callback interaction is needed

### Use `device_harness` when:

- poller writes cache entries consumed by daemon
- timing and race behavior must be asserted
- two role copies of the same device are needed

Typical pattern:

1. create daemon and poller copies
2. trigger poller callback or backend event
3. assert daemon read/status/isCompleted logic

This is the right level for issues like stale cache, fresh readback completion,
and race windows around move-and-wait behavior.

## Full Fixture/Setup Guidance

Use session fixture style for setup-level behavior, not as first choice for all
device behavior.

Checklist for this style:

- keep setup scope as small as possible
- mock external systems explicitly (EPICS/Kafka/network/filesystem)
- avoid broad setup trees unless needed for the assertion
- isolate teardown clearly (`unloadSetup`, session type reset)

## Pattern: Separate Core Logic From Device Wrapper

For complex devices (for example devices using kafka consumer or p4pwrapper), split code into:

- pure logic module: transformations, selection, validation, state updates
- device: NICOS params, session interactions, cache/status calls,
  backend I/O

Test strategy:

1. test pure logic module with standard unit tests
2. test wrapper-device behavior with harness tests
3. add setup/smoke tests only for wiring and process integration risk

This keeps most tests fast and stable, and still validates real NICOS paths.

## Keeping Harness Honest

Harnesses are intentionally lightweight models.
They are protected against divergence from their real counterparts using
contract tests:

- `test/nicos_ess/test_devices/test_device_harness_contract.py`
- `test/nicos_ess/test_devices/test_epics_pva_backend_contract.py`

Contract tests should fail the moment when NICOS session/cache or backend wrapper
interfaces change.

## Running Tests

Run from your active Python environment:

```bash
pytest -q test/nicos_ess
```

Targeted runs:

```bash
pytest -q test/nicos_ess/test_devices/test_epics_devices_harness.py
pytest -q test/nicos_ess/test_devices/test_forwarder.py
```

Use `--confcutdir=test/nicos_ess/` option make pytest ignore conftest files outside of nicos_ess.

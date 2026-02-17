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

Example:

- in Kafka-related code, separate payload conversion or stream-selection logic
  into plain functions/classes and test those directly
- keep device tests focused on device wiring (calls, cache/status side effects)

### 2. Harness-Based Device Tests (Recommended Default For Device Behavior)

Use `test/nicos_ess/device_harness.py` fixtures from
`test/nicos_ess/conftest.py`:

- `daemon_device_harness`: single-session daemon-style tests
- `device_harness`: dual-session daemon+poller tests with shared in-memory cache

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

### 3. Full Fixture/Setup Tests (Old Session Fixture Style)

Use the global `session` fixture (`test/conftest.py`) and setup loading via
`session.loadSetup(...)` as seen in tests like `test_forwarder.py`.

Good fit:

- verifying real setup wiring and attached device chains
- setup import/load behavior
- configuration-level behavior that depends on setup files
- compatibility checks for long-standing setup conventions

Why:

- closer to real NICOS session/setup behavior
- catches integration issues that harness tests intentionally abstract

Limitations:

- heavier and stateful
- slower and harder to debug
- timing/race scenarios are harder to make deterministic

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

Use higher layers only to cover risks not covered below.

## Recommended Split For New Device Work

For most new ESS device behavior:

- mostly pure unit tests for isolated logic
- then harness tests for NICOS device behavior
- then a small number of full fixture/setup checks
- then a minimal smoke test path for critical production flows

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

Use old fixture style for setup-level behavior, not as first choice for all
device logic.

Checklist for this style:

- keep setup scope as small as possible
- mock external systems aggressively
- avoid broad setup trees unless needed for the assertion
- isolate teardown clearly (`unloadSetup`, session type reset)

## Pattern: Separate Core Logic From Device Wrapper

For complex devices (for example Kafka-forwarder-like behavior), split code into:

- pure logic module: transformations, selection, validation, state updates
- device wrapper: NICOS params, session interactions, cache/status calls,
  backend I/O

Test strategy:

1. test pure logic module with standard unit tests
2. test wrapper-device behavior with harness tests
3. add setup/smoke tests only for wiring and process integration risk

This keeps most tests fast and stable, and still validates real NICOS paths.

## Keeping Harness Honest

Harnesses are intentionally lightweight models. Protect against drift using
contract tests:

- `test/nicos_ess/test_devices/test_device_harness_contract.py`
- `test/nicos_ess/test_devices/test_epics_pva_backend_contract.py`

Contract tests should fail quickly when NICOS session/cache or backend wrapper
interfaces change.

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

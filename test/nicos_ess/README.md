# ESS Testing Guide

This document explains how to test ESS NICOS code and when to use each test
style:

- pure unit tests
- harness-based device tests
- GUI harness tests
- full fixture/setup tests
- smoke tests (Not yet implemented)
- integration tests (Not yet implemented)

The goal is to keep tests fast and reliable while still covering real NICOS
behavior where it matters.

## Why Multiple Test Styles

NICOS device code sits between:

- NICOS session/cache/daemon/poller behavior
- facility setup loading (`loadSetup`, attached devices, aliases)
- external systems (EPICS, Kafka, filewriter, network)

No single test style gives strong coverage across all three without tradeoffs.
Use the smallest style that can validate the behavior.

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
- keep device tests focused on NICOS wrapper behavior (backend calls, cache/status
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

### 3. GUI Harness Tests

Use for GUI behavior that needs the real ESS `MainWindow`, `NicosGuiClient`,
panel classes, Qt signals, and the GUI client's event thread.

GUI harness tests fake only the daemon transport. They are closer to focused
GUI smoke/contract tests than business-logic tests: use them to prove a panel
starts, is wired into the real client/window lifecycle, and reacts to
daemon-shaped cache/message/status updates.

Good fit:

- panel startup and teardown
- panel-to-window and panel-to-client wiring
- real Qt signal handling and event-thread delivery
- cache, message, setup, mode, and status update handling in panels

Not a good fit:

- pure device or domain logic
- setup-file import/loading behavior
- real daemon/cache/poller/service process integration
- detailed business-logic matrices that can run below the GUI layer

Why:

- exercises real GUI production classes while staying in-process
- catches broken panel assumptions that unit tests miss
- avoids external services and display-server dependencies

### 4. Full Fixture/Setup Tests

Session fixture style (`test/conftest.py` global `session` fixture).

Use the global `session` fixture (`test/conftest.py`) and setup loading via
`session.loadSetup(...)` as seen in tests like `test_forwarder.py`.

Good fit:

- verifying real setup loading and attached device chains
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
- timing-sensitive behaviors (such as races between session, logger, and cache
  startup) can result in rare, hard-to-reproduce failure modes

### 5. Smoke Tests

Use when validating that services start and basic paths work:

- cache + poller + collector + daemon startup
- basic EPICS PVA connectivity
- service health checks

Good fit:

- startup/order assumptions
- verifying that services come up correctly
- basic end-to-end path checks

### 6. Integration Tests (Full Stack)

Use when validating cross-service behavior across real services/processes:

- cache + poller + collector + daemon interaction
- Kafka broker and topics
- EPICS PVA server round-trips

Good fit:

- cross-process communication
- environment and deployment parity checks
- end-to-end data flow verification

These are high-value but should be a small, focused set because they are the
most expensive and the most failure-prone due to dependency on external
processes, network variability, and environment differences between developer
machines and CI.

## Decision Rule For New Tests

Start at the lowest layer that can prove the requirement:

1. If logic can be isolated from NICOS device classes, write pure unit tests.
2. If behavior depends on device lifecycle/sessiontype/cache callbacks, write
   harness tests.
3. If behavior depends on real ESS GUI classes, Qt signals, panel startup, or
   GUI client event plumbing, write GUI harness tests.
4. If behavior depends on setup loading/attach chains/config wiring, add full
   fixture/setup tests.
5. If behavior depends on real processes/network startup order, add smoke tests.

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

### What Harness Classes Provide

The harness API (`test/nicos_ess/device_harness.py`) exposes:

- `create(role, devcls, name=..., **config)`: create a device under a specific
  role (`"daemon"` or `"poller"`)
- `create_pair(devcls, name=..., shared=..., daemon=..., poller=...)`: create
  daemon+poller copies with shared defaults and per-role overrides
- `run(role, callable, *args)`: execute a callable in a specific role context
- `fake_epics_backend_factory` (fixture): patches EPICS wrapper creation for a
  module, returning a controllable fake backend with `emit_update`,
  `emit_connection`, and inspectable `values`, `alarms`, `put_calls`, etc.

## GUI Harness Tests

ESS GUI harness tests live under `test/nicos_ess/gui` and run the real ESS
`MainWindow`, `NicosGuiClient`, and panels against an in-process fake daemon.
Only the daemon transport is faked; the window, client, panels, Qt signals, and
client event thread are production code.

Treat these as focused GUI smoke/contract tests. They should verify that the GUI
surface starts and responds to daemon-shaped inputs, not carry detailed device
or domain business logic that can be tested faster below the GUI layer.

Use GUI harness tests for:

- panel startup and teardown
- panel wiring to `MainWindow` and `NicosGuiClient`
- client/event-thread plumbing
- panel reactions to cache, message, setup, mode, and status updates

Do not use GUI harness tests for:

- pure device logic
- setup loading or setup import behavior
- real daemon/cache/poller/service process integration
- exhaustive business-logic cases that do not need Qt or the GUI client

Use the file-based guiconfigs under `test/nicos_ess/gui/guiconfigs` only when a
test needs a real multi-panel layout or panel-specific options:

- `base.py` for generic window/client smoke tests
- `estia/selene.py` for the ESTIA Selene panel's custom options
- `command_console.py` for deliberate multi-panel command/console wiring

### Basic patterns

GUI test modules can declare:

- `single_panel_guiconfig_text("pkg.Panel", option=value)` for the common
  generated single-panel path
- `GuiConfigSpec(text=single_panel_guiconfig_text(...))` when an indirect
  fixture parameter should carry generated config text
- `pytest.mark.parametrize("gui_window", [GuiConfigSpec(name="...")],
  indirect=True)` to select a file-based layout through the shared
  `gui_window` fixture
- `pytest.mark.parametrize("gui_panel", ["pkg.Panel"], indirect=True)` when a
  file-based layout test needs the shared `gui_panel` fixture
- `panel_case(...)` in `test_startup.py` for parametrized panel startup and
  minimal status-transition coverage

Keep widget-search helpers local to the panel test module unless at least two
panel suites need the same helper.

### Process-global setup

`test/nicos_ess/gui/conftest.py` forces `QT_QPA_PLATFORM=offscreen` before
pytest-qt creates the `QApplication`, so CI without an X server can still run
the GUI harness. The original value is restored during pytest unconfigure.

The same hook force-loads `pytest-qt` if entry-point plugin autoloading is
disabled, because these tests require both `qtbot` and `qt_log_ignore`.

Two Qt log patterns are silenced globally: the platform-native system tray
signal warning and the `propagateSizeHints()` notice. Add new global GUI noise
to `_IGNORED_QT_MESSAGE_PATTERNS` instead of adding per-test suppressions.

### Fake daemon extension points

Seed daemon state with `fake_daemon.add_device(DeviceSpec(...))` and
`fake_daemon.add_setup("name", loaded=True)`. Startup cases can pass
`seed_daemon=` to `panel_case(...)`; `seed_spectrometer_devices` in
`test_startup.py` is the reference example.

Live updates should go through the fake daemon event helpers: `push_cache`,
`push_setup`, `push_message`, `push_status`, `push_mode`, and
`push_simmessage`. These use the real client signal plumbing, so tests should
wait with `qtbot.waitSignal(window.client.<signal>)` or the `qtbot.waitUntil`
pattern used in `test_devices_panel.py`.

The default strict fake-daemon check asserts that unexpected daemon commands
stay empty. Tests that intentionally exercise misses can request
`allow_unknown_fake_daemon_calls`; otherwise, implement or seed the missing
command. Unknown evals return `None` and are recorded in
`fake_daemon.unknown_evals` for direct assertions; add expected eval replies to
`_seed_gui_defaults` or test-local seeding.

`record_modal_message_boxes` records static `QMessageBox` calls. Critical and
warning dialogs fail by default; information and question dialogs are only
recorded. Request `allow_critical_message_boxes` or
`allow_warning_message_boxes` only in tests that intentionally exercise those
modal paths.

Prefer `single_panel_guiconfig_text` over checking in a guiconfig file unless a
panel needs nested or richer options that are clearer as a file under
`test/nicos_ess/gui/guiconfigs`.

### Runtime resources

The GUI harness wires `resources/` into `test/root/resources` through
`ensure_runtime_resources`. On platforms that cannot create symlinks, the
helper falls back to a real copy and wipes then re-copies it at each session
start, so source changes always propagate. This is cheap while the resources
tree is small; if it grows substantially, switch the tests back to requiring
symlinks.

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

From the workspace, prefer uv commands that install all workspace packages.
GUI tests also need the root `gui` extra, which provides the Qt binding used by
`nicos.guisupport.qt`.

```bash
uv run --frozen --all-packages --extra gui pytest -q test/nicos_ess
```

Targeted runs:

```bash
uv run --frozen --all-packages --extra gui pytest -q test/nicos_ess/gui
uv run --frozen --all-packages pytest -q test/nicos_ess/test_devices/epics_devices/
uv run --frozen --all-packages pytest -q test/nicos_ess/test_devices/test_forwarder.py
```

Use `--confcutdir=test/nicos_ess/` to make pytest ignore conftest files outside
of `test/nicos_ess`.

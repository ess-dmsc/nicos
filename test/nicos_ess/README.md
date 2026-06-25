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

Good fit:

- panel startup and basic lifecycle coverage
- real client/window signal wiring
- panel reactions to daemon protocol-shaped cache, message, setup, mode, and
  status updates

Why:

- keeps the production GUI shell, client, panels, signals, and event thread
- avoids a real daemon process, network service, cache, and poller
- gives focused smoke/contract coverage for GUI surfaces

Limitations:

- fakes only the daemon transport and selected daemon replies
- does not cover setup-file loading, setup imports, or real service integration
- should not carry detailed device/domain logic that can be tested below the GUI
  layer

See the dedicated "GUI Harness Tests" section below for fixture APIs,
guiconfig patterns, and strictness rules.

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
surface starts and responds to daemon protocol-shaped inputs, not carry
detailed device or domain business logic that can be tested faster below the
GUI layer.

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

Use the file-based guiconfigs under `test/nicos_ess/gui/guiconfigs` when a test
needs a real multi-panel layout or panel-specific options:

- `base.py` for generic window/client smoke tests
- `estia/selene.py` for the ESTIA Selene panel's custom options
- `command_console.py` for deliberate multi-panel command/console wiring

### Basic Patterns

Provided fixtures:

- `fake_daemon`: an in-process daemon model that can be seeded before connecting
  a GUI window.
- `gui_window_factory`: builds a real ESS GUI window from either
  `relative_path="..."` or `guiconfig_string="..."`.
- `gui_window`: builds `base.py` by default, or a `GuiConfigSpec` passed through
  indirect parametrization.
- `gui_panel`: retrieves one panel class from `gui_window`; use it only when an
  indirect panel parameter makes the test clearer.

Indirect parametrization:

- Use `GuiConfigSpec(source_string=single_panel_guiconfig_string(...))` when a
  parametrized case should carry a generated config string.
- Use `GuiConfigSpec(relative_path="command_console.py")` when a parametrized
  case should use a checked-in layout.
- For one-off layout tests, call `gui_window_factory(relative_path="...")`
  directly and retrieve panels with `get_panel_by_class(...)`.

Helper routines:

- `single_panel_guiconfig_string("pkg.Panel", option=value)` returns an executable
  guiconfig source string for `processGuiConfig`, not a file path.
- `single_panel_guiconfig_string()` kwargs must be literal-safe: strings, numbers,
  booleans, `None`, lists/tuples of those values, or dicts with string keys and
  literal-safe values. For nested or richer options, check in a file-based
  guiconfig.
- `panel_case(...)` is the `test_startup.py` helper for parametrized panel
  startup and minimal status-transition coverage.
- `get_panel_by_class(...)` asserts that exactly one real panel of the requested
  class exists in the current window.

Minimal example, following the direct-factory style used by current panel tests:

```python
from test.nicos_ess.gui.helpers import (
    get_panel_by_class,
    single_panel_guiconfig_string,
)


guiconfig_string = single_panel_guiconfig_string(
    "nicos_ess.gui.panels.console.ConsolePanel"
)


def test_console_panel_starts(gui_window_factory):
    window = gui_window_factory(guiconfig_string=guiconfig_string)
    panel = get_panel_by_class(window, "nicos_ess.gui.panels.console.ConsolePanel")

    assert panel.isVisible() is True
```

File-based guiconfigs intentionally repeat the minimal shell so each file is a
self-contained source document for `processGuiConfig`. Keep generated and
checked-in guiconfigs aligned on these defaults:

- `options["facility"] == "ess"`
- `options["mainwindow_class"] == "nicos_ess.gui.mainwindow.MainWindow"`
- `windows = []`
- `tools = []`

Drift in those defaults can make file-based layouts exercise a different GUI
shell than generated startup cases. Multi-panel file layouts should be navigated
with `get_panel_by_class(...)` so tests assert the specific panel wiring they
need.

Local conventions:

- Keep widget-search helpers local to the panel test module unless at least two
  panel suites need the same helper.

Startup inventory maintenance:

- `test_startup.py` is curated from production `nicos_ess/**/guiconfig.py`
  files.
- When a production guiconfig adds a top-level `panel(...)`, check whether the
  panel class already has a startup case.
- `grep -R "panel(" nicos_ess --include='guiconfig.py'` is the quick inventory
  refresh.
- Plain `STARTUP_CASE_GROUPS` names mirror instrument package names, while
  `*-panels` groups cover reusable panel subpackages.

### Process-global setup

`test/nicos_ess/gui/conftest.py` forces `QT_QPA_PLATFORM=offscreen` before
pytest-qt creates the `QApplication`, so CI without an X server can still run
the GUI harness. If `XDG_RUNTIME_DIR` is unset, the same hook creates a private
runtime directory to keep Qt from warning during application startup. The
original values are restored during pytest unconfigure.

The same hook force-loads `pytest-qt` if entry-point plugin autoloading is
disabled, because these tests require both `qtbot` and `qt_log_ignore`.

Two Qt log patterns are silenced globally: the platform-native system tray
signal warning and the `propagateSizeHints()` notice. Add new global GUI noise
to `_IGNORED_QT_MESSAGE_PATTERNS` instead of adding per-test suppressions.

GUI windows are constructed with a `NicosLogger` because `MainWindow` uses NICOS
logger helpers such as `error(..., exc=...)`. The fixture parents that logger
into the stdlib logging tree so `caplog` still observes GUI warnings/errors.

Qt and stdlib logging are intentionally split. Pytest-qt captures Qt messages
and `pytest.ini` fails tests on non-ignored Qt warnings or critical messages.
The GUI helper assertions inspect stdlib NICOS log records only.

The GUI window fixture sets `config.stylefile = ""` because `processGuiConfig()`
does not create that attribute. Production `nicos_ess.gui.main` resolves and
applies the ESS QSS before constructing `MainWindow`; the panel harness starts at
the already-processed window/client boundary and deliberately excludes
stylesheet discovery from panel startup coverage.

GUI teardown calls the real `window.close()` path, including panel
`requestClose()`, settings save, child-window close, and client disconnect. The
fixture neutralizes only `QApplication.quit()` because pytest-qt shares one
process-global application across tests.

### Fake daemon extension points

Seed daemon state with `fake_daemon.add_device(DeviceSpec(...))` and
`fake_daemon.add_setup("name", loaded=True)`. When adding a device and setup in
one step, use `fake_daemon.add_device(..., setup="name", loaded=True)`.
Startup cases can pass
`seed_daemon=` to `panel_case(...)`; `seed_spectrometer_devices` in
`test_startup.py` is the reference example.

Small inline seeding example:

```python
from test.nicos_ess.gui.doubles import DeviceSpec


fake_daemon.add_device(
    DeviceSpec(
        name="sample_motor",
        valuetype=float,
        params={"value": 1.0, "status": (200, "idle")},
    ),
    setup="instrument",
    loaded=True,
)
```

Live updates should go through the fake daemon event helpers: `push_cache`,
`push_setup`, `push_message`, `push_status`, `push_mode`, and
`push_simmessage`. These use the real client signal plumbing, so tests should
wait with `qtbot.waitSignal(window.client.<signal>)` or the `qtbot.waitUntil`
pattern used in `test_devices_panel.py`.

Modal `QMessageBox` calls are intercepted so tests do not enter a modal event
loop. Calls are recorded, and warning/critical message boxes fail by default.
Request `allow_critical_message_boxes` or `allow_warning_message_boxes` only for
intentional modal error/warning paths. Request `allow_unpatched_message_boxes`
only for pure transport-contract tests that do not construct GUI code.

Unknown fake-daemon commands and evals are a separate strictness check. Request
`allow_unknown_fake_daemon_requests` only when a test intentionally exercises an
unknown command or eval. Otherwise, seed the missing eval or implement the
missing fake-daemon command response.

Fake daemon boundary:

- Seed `fake_daemon.evals[...]` only when a panel reads a daemon expression and
  the reply is part of the GUI contract being exercised.
- Implement `FakeDaemon.handle(...)` command responses only for daemon commands
  used by the real GUI client or panels under test.
- Use `push_*` event helpers for live cache/message/setup/mode/status behavior;
  they keep the real GUI client signal path in play.
- Use `device_harness`, `daemon_device_harness`, or full setup tests instead
  when the assertion is about Python device behavior, setup loading, setup
  imports, or cache/poller internals rather than GUI protocol handling.

Prefer `single_panel_guiconfig_string` over checking in a guiconfig file unless a
panel needs nested or richer options that are clearer as a file under
`test/nicos_ess/gui/guiconfigs`.

### Runtime resources

The GUI harness wires `resources/` into `test/root/resources` through
`link_or_copy_runtime_resources`. The helper keeps the historical
`config.nicos_root/resources` layout available by replacing stale destinations
with a symlink, or with a fresh copy on platforms where symlinks are
unavailable.

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

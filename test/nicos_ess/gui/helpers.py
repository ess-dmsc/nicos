"""Helpers for ESS GUI panel startup and lifecycle tests.

Use checked-in files under ``test/nicos_ess/gui/guiconfigs`` when generated
single-panel config text becomes too cumbersome.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nicos.guisupport.qt import QApplication
from nicos.protocols.daemon import STATUS_IDLE, STATUS_RUNNING
from nicos.utils import importString


ESS_TEST_FACILITY = "ess"
GUICONFIGS_DIR = Path(__file__).with_name("guiconfigs").resolve()
SeedDaemon = Callable[[Any], None]


@dataclass(frozen=True)
class GuiConfigSpec:
    """Indirect-fixture value for either a checked-in or generated guiconfig."""

    name: str | None = None
    text: str | None = None

    def __post_init__(self):
        if (self.name is None) == (self.text is None):
            raise ValueError(
                "GuiConfigSpec requires exactly one of 'name' or 'text'"
            )


@dataclass(frozen=True)
class StartupCase:
    """One parametrized panel startup scenario for ``test_startup.py``."""

    case_id: str
    panel_class: str | type
    guiconfig: GuiConfigSpec
    seed_daemon: SeedDaemon | None = None
    marks: tuple = ()


def _validate_guiconfig_value(value: Any) -> None:
    """Restrict kwargs so ``repr()`` cannot inject code at config exec time."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_guiconfig_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "GUI test guiconfig kwargs only support string dict keys, "
                    f"got {type(key).__name__}"
                )
            _validate_guiconfig_value(item)
        return
    raise TypeError(
        "GUI test guiconfig kwargs only support literal-safe values, "
        f"got {type(value).__name__}"
    )


def resolve_guiconfig_path(guiconfig_name: str) -> Path:
    """Resolve a GUI test config name inside the checked-in guiconfig tree."""
    if not isinstance(guiconfig_name, str) or not guiconfig_name:
        raise ValueError(
            "GUI test guiconfig_name must be a non-empty relative path, "
            "for example 'command_console.py'"
        )
    guiconfig_path = (GUICONFIGS_DIR / guiconfig_name).resolve()
    try:
        guiconfig_path.relative_to(GUICONFIGS_DIR)
    except ValueError as err:
        raise ValueError(
            f"GUI test guiconfig_name must stay inside {GUICONFIGS_DIR}: "
            f"{guiconfig_name!r}"
        ) from err
    if not guiconfig_path.is_file():
        raise FileNotFoundError(
            f"GUI test guiconfig not found: {guiconfig_name!r} -> {guiconfig_path}"
        )
    return guiconfig_path


def single_panel_guiconfig_text(panel_cls, **panel_kwargs):
    """Render an executable guiconfig source string with one root panel.

    Produced text is ``exec``d by ``processGuiConfig``; kwargs are stamped via
    ``repr()`` and validated against a literal-only whitelist
    (``_validate_guiconfig_value``) so a test cannot smuggle arbitrary code or
    non-deterministic objects into the generated config.
    """
    for value in panel_kwargs.values():
        _validate_guiconfig_value(value)
    panel_path = (
        panel_cls
        if isinstance(panel_cls, str)
        else f"{panel_cls.__module__}.{panel_cls.__qualname__}"
    )
    panel_args = [repr(panel_path)]
    panel_args.extend(f"{name}={value!r}" for name, value in panel_kwargs.items())
    if len(panel_args) == 1:
        main_window = f"main_window = panel({panel_args[0]})"
    else:
        joined_args = ",\n    ".join(panel_args)
        main_window = f"main_window = panel(\n    {joined_args},\n)"
    return (
        f"{main_window}\n"
        "windows = []\n"
        "tools = []\n"
        'options = {\n'
        f'    "facility": "{ESS_TEST_FACILITY}",\n'
        '    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",\n'
        "}\n"
    )


def panel_case(
    case_id,
    panel_class,
    *,
    guiconfig_name=None,
    seed_daemon=None,
    marks=(),
    **panel_kwargs,
):
    """Create a startup case from either generated text or a guiconfig file."""
    if guiconfig_name is None:
        guiconfig = GuiConfigSpec(
            text=single_panel_guiconfig_text(panel_class, **panel_kwargs)
        )
    else:
        guiconfig = GuiConfigSpec(name=guiconfig_name)
    return StartupCase(
        case_id=case_id,
        panel_class=panel_class,
        guiconfig=guiconfig,
        seed_daemon=seed_daemon,
        marks=marks,
    )


def get_panel_by_class(window, panel_class):
    panel_cls = (
        importString(panel_class) if isinstance(panel_class, str) else panel_class
    )
    # Startup tests are meant to instantiate the requested panel class, not an
    # arbitrary subclass that happens to satisfy the same interface.
    matches = [panel for panel in window.panels if type(panel) is panel_cls]
    assert len(matches) == 1, (
        f"expected one {panel_cls.__module__}.{panel_cls.__name__} panel, "
        f"found {[type(panel).__name__ for panel in window.panels]}"
    )
    return matches[0]


_RELEVANT_LOGGER_PREFIXES = ("nicos", "nicos_ess")


def _is_relevant_gui_record(record):
    """Filter caplog records to those produced by NICOS code.

    Filters by logger name, which is controlled by NICOS itself, instead of
    file path so the helper works regardless of checkout location and ignores
    third-party Qt/matplotlib warnings that we do not own.
    """
    name = (record.name or "").split(".", 1)[0]
    return name in _RELEVANT_LOGGER_PREFIXES


def _assert_no_unexpected_nicos_logs(caplog):
    """Catch NICOS warnings/errors that do not crash panel startup.

    Defense-in-depth: panel readiness is the primary signal; this catches
    silent NICOS-level warnings/errors that would otherwise be lost, for
    example cache lookup failures.
    """
    relevant_records = [
        record for record in caplog.records if _is_relevant_gui_record(record)
    ]
    warnings_or_errors = [
        record for record in relevant_records if record.levelno >= logging.WARNING
    ]
    assert warnings_or_errors == [], "unexpected GUI log records:\n" + "\n".join(
        f"{record.levelname} {record.name}: {record.getMessage()}"
        for record in warnings_or_errors
    )


def _assert_panel_is_alive(window, panel):
    assert panel in window.panels
    assert panel.isVisible() is True
    assert window.client.isconnected is True


def _build_panel(gui_window_factory, startup_case, fake_daemon, caplog):
    if startup_case.seed_daemon is not None:
        startup_case.seed_daemon(fake_daemon)
    caplog.clear()
    caplog.set_level(logging.WARNING)
    if startup_case.guiconfig.text is not None:
        window = gui_window_factory(guiconfig=startup_case.guiconfig.text)
    else:
        window = gui_window_factory(
            guiconfig_path=resolve_guiconfig_path(startup_case.guiconfig.name)
        )
    QApplication.processEvents()
    return window, get_panel_by_class(window, startup_case.panel_class)


def assert_panel_starts_clean(gui_window_factory, startup_case, fake_daemon, caplog):
    """Assert that a panel starts without NICOS warnings or errors."""
    window, panel = _build_panel(
        gui_window_factory=gui_window_factory,
        startup_case=startup_case,
        fake_daemon=fake_daemon,
        caplog=caplog,
    )
    _assert_panel_is_alive(window, panel)
    _assert_no_unexpected_nicos_logs(caplog)
    return panel


def assert_panel_survives_minimal_status_transitions(
    gui_window_factory,
    startup_case,
    fake_daemon,
    caplog,
    qtbot,
):
    """Assert that a panel survives setup and running/idle status events."""
    window, panel = _build_panel(
        gui_window_factory=gui_window_factory,
        startup_case=startup_case,
        fake_daemon=fake_daemon,
        caplog=caplog,
    )
    _assert_no_unexpected_nicos_logs(caplog)

    caplog.clear()

    if not fake_daemon.setups:
        fake_daemon.add_setup("system")
    loaded_setups = sorted(fake_daemon.loaded_setups)
    if not loaded_setups:
        loaded_setups = sorted(fake_daemon.setups)

    with qtbot.waitSignal(window.client.setup, timeout=2000):
        fake_daemon.push_setup(loaded_setups)
    _assert_panel_is_alive(window, panel)

    # Status payloads are (status_code, lineno); -1 means "no active line".
    with qtbot.waitSignal(window.client.status, timeout=2000):
        fake_daemon.push_status((STATUS_RUNNING, -1))
    _assert_panel_is_alive(window, panel)

    with qtbot.waitSignal(window.client.status, timeout=2000):
        fake_daemon.push_status((STATUS_IDLE, -1))
    _assert_panel_is_alive(window, panel)

    thread = getattr(window.client, "event_thread", None)
    window.client.disconnect()
    qtbot.waitUntil(lambda w=window: not w.client.isconnected, timeout=2000)
    if thread is not None:
        qtbot.waitUntil(lambda t=thread: not t.is_alive(), timeout=2000)
    QApplication.processEvents()

    _assert_no_unexpected_nicos_logs(caplog)
    return panel

"""Helpers for ESS GUI panel startup and lifecycle tests."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import pytest

from nicos.guisupport.qt import QApplication
from nicos.protocols.daemon import STATUS_IDLE, STATUS_RUNNING
from nicos.utils import importString


ESS_TEST_FACILITY = "ess"
SeedDaemon = Callable[[Any], None]


@dataclass(frozen=True)
class GuiConfigSpec:
    name: str | None = None
    text: str | None = None

    def __post_init__(self):
        if (self.name is None) == (self.text is None):
            raise ValueError(
                "GuiConfigSpec requires exactly one of 'name' or 'text'"
            )


@dataclass(frozen=True)
class StartupCase:
    case_id: str
    panel_class: str | type
    guiconfig: GuiConfigSpec
    seed_daemon: SeedDaemon | None = None


def _validate_guiconfig_value(value: Any) -> None:
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


def _minimal_guiconfig(panel_cls, **panel_kwargs):
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
    if guiconfig_name is None:
        guiconfig = GuiConfigSpec(text=_minimal_guiconfig(panel_class, **panel_kwargs))
    else:
        guiconfig = GuiConfigSpec(name=guiconfig_name)
    return pytest.param(
        StartupCase(
            case_id=case_id,
            panel_class=panel_class,
            guiconfig=guiconfig,
            seed_daemon=seed_daemon,
        ),
        id=case_id,
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


def _is_relevant_gui_record(record):
    pathname = record.pathname.replace("\\", "/")
    return "/nicos/" in pathname or "/nicos_ess/" in pathname


def _assert_no_warnings_or_errors(caplog):
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


def _build_panel(gui_window_from_spec, startup_case, fake_daemon, caplog):
    if startup_case.seed_daemon is not None:
        startup_case.seed_daemon(fake_daemon)
    caplog.clear()
    caplog.set_level(logging.WARNING)
    window = gui_window_from_spec(startup_case.guiconfig)
    QApplication.processEvents()
    return window, get_panel_by_class(window, startup_case.panel_class)


def assert_panel_starts_clean(gui_window_from_spec, startup_case, fake_daemon, caplog):
    _, panel = _build_panel(
        gui_window_from_spec=gui_window_from_spec,
        startup_case=startup_case,
        fake_daemon=fake_daemon,
        caplog=caplog,
    )
    _assert_no_warnings_or_errors(caplog)
    return panel


def assert_panel_survives_minimal_status_transitions(
    gui_window_from_spec,
    startup_case,
    fake_daemon,
    caplog,
    qtbot,
):
    window, panel = _build_panel(
        gui_window_from_spec=gui_window_from_spec,
        startup_case=startup_case,
        fake_daemon=fake_daemon,
        caplog=caplog,
    )
    _assert_no_warnings_or_errors(caplog)

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

    _assert_no_warnings_or_errors(caplog)
    return panel

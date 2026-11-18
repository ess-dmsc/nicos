"""Helpers for ESS GUI panel startup and lifecycle tests.

Use checked-in files under ``test/nicos_ess/gui/guiconfigs`` when generated
single-panel config strings become too cumbersome.
"""

from __future__ import annotations

import contextlib
import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nicos.guisupport.qt import (
    QApplication,
    QDialog,
    QEvent,
    QMenu,
    QMouseEvent,
    QPointF,
    Qt,
)
from nicos.guisupport.typedvalue import DeviceValueEdit
from nicos.protocols.daemon import STATUS_IDLE, STATUS_RUNNING
from nicos.utils import importString

ESS_TEST_FACILITY = "ess"
GUICONFIGS_DIR = Path(__file__).with_name("guiconfigs").resolve()
SeedDaemon = Callable[[Any], None]


@dataclass(frozen=True)
class GuiConfigSpec:
    """Indirect-fixture value for either a checked-in or generated guiconfig."""

    relative_path: str | None = None
    source_string: str | None = None

    def __post_init__(self):
        if (self.relative_path is None) == (self.source_string is None):
            raise ValueError(
                "GuiConfigSpec requires exactly one of "
                "'relative_path' or 'source_string'"
            )


@dataclass(frozen=True)
class StartupCase:
    """One parametrized panel startup scenario for ``test_startup.py``."""

    case_id: str
    panel_class: str | type
    guiconfig: GuiConfigSpec
    seed_daemon: SeedDaemon | None = None
    expert_mode: bool = False
    marks: tuple = ()


def _validate_guiconfig_value(value: Any) -> None:
    """Restrict kwargs to deterministic values for generated config strings."""
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


def resolve_guiconfig_path(relative_path: str) -> Path:
    """Resolve a GUI test config name inside the checked-in guiconfig tree."""
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(
            "GUI test guiconfig relative_path must be non-empty, "
            "for example 'command_console.py'"
        )
    guiconfig_path = (GUICONFIGS_DIR / relative_path).resolve()
    try:
        guiconfig_path.relative_to(GUICONFIGS_DIR)
    except ValueError as err:
        raise ValueError(
            f"GUI test guiconfig relative_path must stay inside {GUICONFIGS_DIR}: "
            f"{relative_path!r}"
        ) from err
    if not guiconfig_path.is_file():
        raise FileNotFoundError(
            f"GUI test guiconfig not found: {relative_path!r} -> {guiconfig_path}"
        )
    return guiconfig_path


def single_panel_guiconfig_string(panel_cls, **panel_kwargs):
    """Render an executable guiconfig source string with one root panel.

    Produced string is ``exec``d by ``processGuiConfig``; kwargs are stamped via
    ``repr()`` and validated against a literal-only whitelist
    (``_validate_guiconfig_value``) so the generated config remains
    deterministic and reviewable.
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
        "options = {\n"
        f'    "facility": "{ESS_TEST_FACILITY}",\n'
        '    "mainwindow_class": "nicos_ess.gui.mainwindow.MainWindow",\n'
        "}\n"
    )


def panel_case(
    *,
    case_id,
    panel_class,
    guiconfig_name=None,
    seed_daemon=None,
    expert_mode=False,
    marks=(),
    **panel_kwargs,
):
    """Create a startup case from either generated string or a guiconfig file."""
    if guiconfig_name is None:
        guiconfig = GuiConfigSpec(
            source_string=single_panel_guiconfig_string(panel_class, **panel_kwargs)
        )
    else:
        guiconfig = GuiConfigSpec(relative_path=guiconfig_name)
    return StartupCase(
        case_id=case_id,
        panel_class=panel_class,
        guiconfig=guiconfig,
        seed_daemon=seed_daemon,
        expert_mode=expert_mode,
        marks=marks,
    )


def _grab_pixels(widget):
    import numpy as np

    from nicos.guisupport.qt import QImage

    image = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    bits = image.constBits()
    bits.setsize(image.sizeInBytes())
    rows = np.frombuffer(bits, np.uint32).reshape(image.height(), -1)
    return rows[:, : image.width()].copy()


def drawn_pixels(widget, item):
    """Return the x and y arrays of the pixels of *widget* that the plot *item*
    draws.

    These are the pixels that change when the item is hidden, so the axes,
    ticks, grid, title and the other curves do not count.
    """
    import numpy as np
    import pyqtgraph as pg

    if not item.isVisible():
        return np.array([], int), np.array([], int)
    boxes = [box for box in item.scene().items() if isinstance(box, pg.ViewBox)]
    # A hidden item would change the auto range and with it the axes.
    auto_ranges = [(box, list(box.state["autoRange"])) for box in boxes]
    for box in boxes:
        box.disableAutoRange()
    item.hide()
    without_item = _grab_pixels(widget)
    item.show()
    with_item = _grab_pixels(widget)
    for box, (x_auto, y_auto) in auto_ranges:
        box.enableAutoRange(pg.ViewBox.XAxis, x_auto)
        box.enableAutoRange(pg.ViewBox.YAxis, y_auto)
    ys, xs = np.nonzero(with_item != without_item)
    return xs, ys


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
    """Fail if NICOS warnings/errors leak during GUI startup or lifecycle."""
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
    if startup_case.guiconfig.source_string is not None:
        window = gui_window_factory(
            guiconfig_string=startup_case.guiconfig.source_string
        )
    else:
        window = gui_window_factory(relative_path=startup_case.guiconfig.relative_path)
    QApplication.processEvents()
    panel = get_panel_by_class(window, startup_case.panel_class)
    if startup_case.expert_mode:
        window.on_actionExpert_toggled(True)
        QApplication.processEvents()
    return window, panel


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


def answer_dialogs(monkeypatch, fill=None, accept=True):
    """Answer every modal ``QDialog.exec()`` without showing it.

    ``fill(dialog)`` runs first and can read or fill in the dialog.
    """

    def fake_exec(dialog):
        if fill is not None:
            fill(dialog)
        if accept:
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", fake_exec)


def set_device_value(dialog, value):
    """Set the value in the only device value editor of ``dialog``."""
    [editor] = dialog.findChildren(DeviceValueEdit)
    editor.setValue(value)


def menu_action(plot_menu, text):
    """Return the entry called *text* from a freshly opened plot menu or one
    of its submenus."""
    menu = plot_menu.menu
    menu.aboutToShow.emit()
    submenus = [a for m in menu.findChildren(QMenu) for a in m.actions()]
    actions = menu.actions() + submenus
    action = next((a for a in actions if a.text() == text), None)
    if action is None:
        raise AssertionError(
            f"The plot menu has no entry {text!r}. "
            f"Its entries are {[a.text() for a in actions]}."
        )
    return action


def mouse_move(qtbot, widget, point, buttons=Qt.MouseButton.LeftButton):
    """Move the mouse to *point* on *widget* with *buttons* held."""
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(point),
        QPointF(widget.mapToGlobal(QPointF(point).toPoint())),
        Qt.MouseButton.NoButton,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, event)
    qtbot.wait(20)


def _press_and_move(qtbot, viewport, start, *ends):
    # The mouse hovers before it presses because pyqtgraph picks the item that
    # a drag moves while hovering.
    mouse_move(qtbot, viewport, start, Qt.MouseButton.NoButton)
    qtbot.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
    for a, b in itertools.pairwise((start, *ends)):
        for i in range(1, 6):
            mouse_move(qtbot, viewport, a + (b - a) * i / 5)


def mouse_drag(qtbot, viewport, start, *ends, settle_ms=150):
    """Drag the mouse from *start* through *ends* on *viewport* the way a hand does.

    After the release the test waits *settle_ms* so that the timers which
    the release starts can run before the next step or the teardown.
    """
    _press_and_move(qtbot, viewport, start, *ends)
    qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=ends[-1])
    qtbot.wait(settle_ms)


@contextlib.contextmanager
def mouse_held(qtbot, viewport, start, *ends):
    """Drag like `mouse_drag` and keep the button down inside the with block.

    The block can release the button anywhere itself. Otherwise the button
    comes up at the last point when the block ends, also when the block
    fails, so a later test does not see a held button.
    """
    try:
        _press_and_move(qtbot, viewport, start, *ends)
        yield
    finally:
        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            qtbot.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=ends[-1])

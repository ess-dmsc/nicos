from nicos.core.status import BUSY, DISABLED, ERROR, NOTREACHED, OK, UNKNOWN, WARN
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    QBrush,
    QFont,
    QPalette,
)
from nicos_ess.gui.utils import get_icon


def convert_limit_to_string(value, fmtstr):
    if abs(value) >= 1e10:
        # Use exponential formatting for big numbers
        return f"{value:.2g}"
    return fmtstr % value


def setBackgroundBrush(widget, color):
    palette = widget.palette()
    palette.setBrush(QPalette.ColorRole.Window, color)
    widget.setBackgroundRole(QPalette.ColorRole.Window)
    widget.setPalette(palette)


def setForegroundBrush(widget, color):
    palette = widget.palette()
    palette.setBrush(QPalette.ColorRole.WindowText, color)
    widget.setForegroundRole(QPalette.ColorRole.WindowText)
    widget.setPalette(palette)


def attach_status_resources(cls):
    # hack to make non-Qt usage as in checksetups work
    if hasattr(cls, "statusIcon"):
        return

    cls.statusIcon = {
        OK: get_icon("check_circle_green-24px.svg"),
        WARN: get_icon("warning_orange-24px.svg"),
        BUSY: get_icon("sync_orange-24px.svg"),
        NOTREACHED: get_icon("error-24px.svg"),
        DISABLED: get_icon("not_interested-24px.svg"),
        ERROR: get_icon("error-24px.svg"),
        UNKNOWN: get_icon("device_unknown-24px.svg"),
    }

    cls.fgBrush = {
        OK: QBrush(colors.dev_fg_ok),
        WARN: QBrush(colors.text),
        BUSY: QBrush(colors.text),
        NOTREACHED: QBrush(colors.text),
        DISABLED: QBrush(colors.text),
        ERROR: QBrush(colors.text),
        UNKNOWN: QBrush(colors.dev_fg_unknown),
    }

    cls.bgBrush = {
        OK: QBrush(),
        WARN: QBrush(colors.dev_bg_warning),
        BUSY: QBrush(colors.dev_bg_busy),
        NOTREACHED: QBrush(colors.dev_bg_error),
        DISABLED: QBrush(colors.dev_bg_disabled),
        ERROR: QBrush(colors.dev_bg_error),
        UNKNOWN: QBrush(),
    }

    # keys: (expired, fixed)
    cls.valueBrush = {
        (False, False): QBrush(),
        (False, True): QBrush(colors.value_fixed),
        (True, False): QBrush(colors.value_expired),
        (True, True): QBrush(colors.value_expired),
    }

    cls.lowlevelBrush = {
        False: QBrush(colors.text),
        True: QBrush(colors.lowlevel),
    }

    cls.lowlevelFont = {
        False: QFont(),
        True: QFont(QFont().family(), -1, -1, True),
    }

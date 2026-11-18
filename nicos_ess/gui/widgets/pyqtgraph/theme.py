"""This module sets the shared look of the pyqtgraph plots."""

import functools
from datetime import datetime

import numpy as np
import pyqtgraph as pg

from nicos.guisupport.qt import QApplication, QFont, QFontInfo, QFontMetricsF, QLabel
from nicos_ess.gui.widgets.pyqtgraph.frame_format import SI

# Any two curve colours have a CIELAB distance above 28, and none of them is
# pale on white.
COLORS = (  # noqa: SIM905
    "#0072b2 #d55e00 #009e73 #e69f00 #cc79a7 #17becf"
    " #6a3d9a #66a61e #7f7f7f #e7298a #882255 #a6761d"
).split()
# The crosshair is opaque with a dark edge so that it shows on any colormap.
CROSS_COLOR = CROSS_HOOVER_COLOR = (255, 165, 0, 255)
CROSS_EDGE = (0, 0, 0, 170)
ROI_COLOR, ROI_HOOVER_COLOR = (7, 188, 230, 180), (7, 188, 230, 255)
LINE_ROI_WIDTH_COLOR = (166, 0, 255, 100)
LINE_ROI_COLOR, LINE_ROI_HOOVER_COLOR = (166, 0, 255, 180), (166, 0, 255, 255)
LINE_ROI_HANDLE_COLOR_LEFT = (255, 0, 0, 180)
LINE_ROI_HANDLE_HOOVER_COLOR_LEFT = (255, 0, 0, 255)
LINE_ROI_HANDLE_COLOR_RIGHT = (0, 0, 0, 180)
LINE_ROI_HANDLE_HOOVER_COLOR_RIGHT = (0, 0, 0, 255)
LINE_WIDTH = 2

# Images offer these matplotlib colormaps and their reversed versions. The
# diverging maps are for data around a middle value and the cyclic maps are
# for angles.
COLORMAP_GROUPS = {
    "Uniform": ("viridis", "plasma", "inferno", "magma", "cividis"),
    "Sequential": ("gray", "bone", "hot", "afmhot", "copper", "pink", "Blues"),
    "Diverging": ("seismic", "coolwarm", "bwr", "RdBu", "RdYlBu", "PiYG", "BrBG"),
    "Cyclic": ("twilight", "twilight_shifted", "hsv"),
    "Rainbow": ("turbo", "jet", "rainbow", "nipy_spectral", "cubehelix", "terrain"),
}
COLORMAPS = tuple(name for names in COLORMAP_GROUPS.values() for name in names)

# Text sizes are relative to the GUI text. The NICOS style sheet sets the GUI
# text to 16 px whatever the application font is.
TICK_SCALE, LABEL_SCALE, TITLE_SCALE = 0.8, 0.85, 0.9
MIN_PX = 8  # This is the smallest text size in px.
# Secondary text such as units and details in a title uses this colour.
MUTED = "#6b6b6b"
# Curve plots draw the line at the pointer with this pen.
POINTER_PEN = pg.mkPen(MUTED, width=1)
# This colour marks things worth noticing, like old data or a frozen view.
ATTENTION = "#b85c00"
ALERT = "#c0392b"
ACCENT = "#0094ca"  # This is the NICOS selection colour from guiconfig.qss.
SLATE = "#32414B"

# Use segmented lines because smooth lines wider than 1 px are otherwise 20 to
# 50 times slower to draw.
pg.setConfigOptions(
    background="w", foreground="k", antialias=True, segmentedLineMode="on"
)


def curve_color(index):
    return pg.mkColor(COLORS[index % len(COLORS)])


def label_room(axis, label):
    """Return the distance in px from one tick to the next that *label* needs
    on *axis*.

    The gap between labels is the same on every axis whatever its length.
    """
    metrics = QFontMetricsF(axis.style["tickFont"])
    if axis.orientation in ("left", "right"):
        return 2.5 * metrics.height()
    return metrics.horizontalAdvance(label) + 1.5 * metrics.height()


def nice_step(least):
    """Return the smallest step of 1, 2 or 5 times a power of 10 that is at
    least *least*, or 1e308, which is the largest such step that is a float."""
    least = min(least, 1e308)
    power = 10.0 ** np.floor(np.log10(least))
    return next(m * power for m in (1, 2, 5, 10) if m * power >= least * 0.999)


class TimeAxisItem(pg.DateAxisItem):
    """This time axis shows local time and is styled by `style_axis`.

    For steps up to an hour, the ticks are at round times as close together
    as `label_room` allows and show the time of day like 18:47:35.5. The
    pyqtgraph ticks would leave spans of seconds with one label or none.
    """

    STEPS = (0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600)

    def __init__(self, orientation, **kwargs):
        super().__init__(orientation, **kwargs)
        style_axis(self)

    def tickValues(self, minVal, maxVal, size):
        if not size or maxVal <= minVal or abs(minVal) > 1e11:
            return super().tickValues(minVal, maxVal, size)
        per_second = size / (maxVal - minVal)
        for step in self.STEPS:
            label = "00:00" if step >= 60 else "00:00:00.0" if step < 1 else "00:00:00"
            if step * per_second >= label_room(self, label):
                break
        else:
            return super().tickValues(minVal, maxVal, size)
        offset = datetime.fromtimestamp(minVal).astimezone().utcoffset().total_seconds()
        first = np.ceil((minVal + offset) / step) * step - offset
        return [(step, list(np.arange(first, maxVal, step)))]

    def tickStrings(self, values, scale, spacing):
        if spacing > 3600:  # tickValues leaves steps above an hour to pyqtgraph.
            return super().tickStrings(values, scale, spacing)
        texts = []
        for value in values:
            try:
                when = datetime.fromtimestamp(value)
            except (OverflowError, OSError, ValueError):
                texts.append("")
                continue
            tenths = f".{when.microsecond // 100_000}" if spacing < 1 else ""
            texts.append(
                when.strftime("%H:%M" if spacing >= 60 else "%H:%M:%S") + tenths
            )
        return texts


def compact_number(value, spacing):
    """Return a short tick label such as 15.8G for 1.58e+10.

    The label has as many digits as ticks *spacing* apart need to differ, for
    example 5.73431M.
    """
    if value == 0:
        return "0"
    for scale, suffix in SI:
        # Write 1000 in full because 1.000k is harder to read.
        if abs(value) >= max(scale, 1e4):
            return f"{value / scale:.{decimals(spacing / scale)}f}{suffix}"
    if abs(value) < 1e-3:
        power = int(np.floor(np.log10(abs(value))))
        return f"{value:.{max(1, power + decimals(spacing))}e}"
    return f"{value:.{decimals(spacing)}f}"


def decimals(spacing):
    """Return the number of decimals that tells numbers *spacing* apart."""
    return max(0, -int(np.floor(np.log10(spacing)))) if spacing > 0 else 0


class CompactAxisItem(pg.AxisItem):
    """Every plot uses this value axis, which is styled by `style_axis`.

    The labels are short because pyqtgraph drops all labels of an axis when
    one of them is wider than the axis. They are as close together as
    `label_room` allows on every axis, whereas pyqtgraph would pick them by
    count. On a log scale the labels show plain values like 1, 10 and 100,
    and only powers of 10 get labels when two of them are in view.

    With ``integers`` set, the ticks are at whole numbers only. If
    ``integers`` is True the labels are written in full, which suits pixels.
    If it is "counts" the labels are short like on the other axes.
    """

    integers = False

    def __init__(self, orientation, **kwargs):
        super().__init__(orientation, **kwargs)
        style_axis(self)
        self.setStyle(maxTextLevel=0)  # Only the major ticks get labels.

    def tickValues(self, minVal, maxVal, size):
        # On a log scale these are the log10 of the values.
        low, high = sorted((minVal, maxVal))
        if self.logMode:
            # Larger powers of 10 are not floats, and a scale switched to log
            # without data keeps a linear range of such powers.
            low, high = max(low, -307.0), min(high, 307.0)
        if not np.isfinite([low, high]).all() or high < low:
            return []
        if not size or high == low:
            return super().tickValues(low, high, size)
        # Inside a single decade the ticks are at steps of the plain values.
        if self.logMode and high - low < 1:
            values, top = 10.0**low, 10.0**high
            step = nice_step((top - values) * label_room(self, "0") / size)
            values = step * np.arange(np.ceil(values / step - 1e-9), top / step + 1e-9)
            return [(step, list(np.log10(values)))]
        # Dividing first keeps the span of the widest axes finite.
        per_pixel = high / size - low / size
        # Log scales step by whole decades and integer axes by whole numbers.
        # Smaller steps than the smallest normal float would round to 0.
        least = 1 if self.logMode or self.integers else np.finfo(float).tiny
        step = self._major_step(low, high, per_pixel, least)
        # Adding 0.0 turns -0 into 0.
        major = step * np.arange(np.ceil(low / step), high / step + 1e-9) + 0.0
        minor = self._minor_ticks(low, high, step)
        return [(step, list(major)), (step / 10, list(minor))]

    def _major_step(self, low, high, per_pixel, least):
        """Return the step between the major ticks, which is at least *least*.

        The labels must fit between the ticks. The step gets smaller when
        fewer than two labels would be clear of the ends of the axis.
        """
        step = nice_step(max(label_room(self, "0") * per_pixel, least))
        # A coarser step can need wider labels, so try again a few times.
        for _ in range(8):
            ends = [np.ceil(low / step) * step, np.floor(high / step) * step]
            room = max(label_room(self, t) for t in self.tickStrings(ends, 1, step))
            if step >= room * per_pixel:
                break
            step = nice_step(max(step * 1.01, room * per_pixel))
        # Labels right at the end of an axis get cut off.
        inset = label_room(self, "0") / 2 * per_pixel
        while np.floor((high - inset) / step) - np.ceil((low + inset) / step) < 1:
            closer = nice_step(step * 0.4)
            if closer < least or closer < label_room(self, "0") / 2.5 * per_pixel:
                break
            step = closer
        return step

    def _minor_ticks(self, low, high, step):
        # The minor ticks are at 2 to 9 times each power of 10.
        if self.logMode and step == 1:
            decades = np.arange(np.floor(low), np.ceil(high))
            minor = (decades[:, None] + np.log10(np.arange(2, 10))).ravel()
        else:
            mantissa = round(step / 10 ** np.floor(np.log10(step)))
            spacing = 1 if self.logMode else step / (2 if mantissa == 2 else 5)
            minor = spacing * np.arange(np.ceil(low / spacing), high / spacing + 1e-9)
        on_major = np.abs(minor / step - np.round(minor / step)) < 1e-6
        return minor[(minor >= low) & (minor <= high) & ~on_major]

    def tickStrings(self, values, scale, spacing):
        if self.logMode or self.integers is True:
            return super().tickStrings(values, scale, spacing)
        return [compact_number(v * scale, spacing * scale) for v in values]

    def logTickStrings(self, values, scale, spacing):
        low, high = sorted(self.range)
        # Only label the powers of 10 when at least one is in view.
        if np.floor(high) - np.ceil(low) >= 1:
            return [
                "" if abs(v - round(v)) > 1e-6 else compact_number(10**v, 10**v)
                for v in values
            ]
        x = 10.0 ** np.asarray(values)
        gaps = np.diff(x)[np.diff(x) > 0]
        step = nice_step(gaps.min()) if gaps.size else x.max(initial=1.0)
        return [compact_number(v, step) for v in x]


def base_pixel_size():
    """Return the pixel size of the GUI text.

    The size is measured on a styled widget because the NICOS style sheet
    overrides the application font.
    """
    app = QApplication.instance()
    if app is None:
        return 12
    return _styled_size(app.styleSheet(), QFontInfo(app.font()).pixelSize())


@functools.cache
def _styled_size(_style_sheet, _app_size):
    probe = QLabel()
    probe.ensurePolished()
    return QFontInfo(probe.font()).pixelSize()


def css_size(scale):
    """Return a font size for the HTML labels of pyqtgraph."""
    return f"{max(MIN_PX, round(base_pixel_size() * scale))}px"


def scaled_font(scale, bold=False):
    font = QFont()
    font.setPixelSize(max(MIN_PX, round(base_pixel_size() * scale)))
    font.setBold(bold)
    return font


def style_axis(axis):
    """Style *axis* with ticks that point into the plot and no SI prefixes.

    Tick labels are short already, and a prefix would turn the unit "ms" into
    "kms". The room for the labels only grows, so the plot does not jump as
    the values change.
    """
    axis.setStyle(
        tickFont=scaled_font(TICK_SCALE),
        tickTextOffset=3,
        tickLength=-4,
        autoReduceTextSpace=False,
    )
    axis.enableAutoSIPrefix(False)
    axis.labelStyle = {"font-size": css_size(LABEL_SCALE), "color": MUTED}


def fix_axis_room(axis, widest="-888.8k", extra=0.0):
    """Keep room on *axis* for the label *widest* plus *extra* px.

    Otherwise the plot jumps a frame later when pyqtgraph sizes the axis to
    the labels.
    """
    metrics, offset = (
        QFontMetricsF(axis.style["tickFont"]),
        axis.style["tickTextOffset"],
    )
    if axis.orientation in ("left", "right"):
        room = metrics.horizontalAdvance(widest) + offset[0] + 2 + extra
        axis.setWidth(int(np.ceil(room)))
    else:
        axis.setHeight(int(np.ceil(metrics.height() + offset[1] + 2 + extra)))
    axis.setStyle(autoExpandTextSpace=False)


def fix_label_size(label, height):
    """Clip the text of *label* so that the text cannot resize the layout.

    pyqtgraph sets the minimum size of a label from its text, which would
    move every plot in a grid.
    """
    label.updateMin = lambda: None
    label.setMinimumSize(0, height)
    label.setMaximumHeight(height)
    label.setFlag(label.GraphicsItemFlag.ItemClipsChildrenToShape)

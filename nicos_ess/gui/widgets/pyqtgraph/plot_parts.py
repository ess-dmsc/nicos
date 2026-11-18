"""This module holds the parts of a plot, such as the title line and the menu."""

import html
import re

import pyqtgraph as pg

from nicos.guisupport.qt import (
    QActionGroup,
    QApplication,
    QDoubleValidator,
    QFontMetricsF,
    QFormLayout,
    QGraphicsTextItem,
    QLineEdit,
    QLocale,
    QMenu,
    QObject,
    QPoint,
    QPointF,
    Qt,
    QWidget,
    QWidgetAction,
    pyqtSignal,
)
from nicos_ess.gui.widgets.pyqtgraph.export import save_plot_dialog
from nicos_ess.gui.widgets.pyqtgraph.theme import (
    MUTED,
    TICK_SCALE,
    TITLE_SCALE,
    css_size,
    fix_label_size,
    scaled_font,
)

FIELD_WIDTH = 110  # The width is in pixels.
MENU_MARKER = " ▾"  # This follows a name that opens a menu.
BOX_FILL, BOX_EDGE = (255, 255, 255, 235), "#c8c8c8"
NUMBER = re.compile(r"–|[-+]?\d[\d.,:]*(?:e[-+]?\d+)?[kMGT]?")


def numbers(fields):
    """Return the numbers in *fields*, or None if any field holds no number."""
    try:
        return [float(field.text()) for field in fields]
    except ValueError:
        return None


def clear_menu(menu):
    """Empty *menu* and delete the submenus, which ``clear()`` alone keeps."""
    for submenu in menu.findChildren(QMenu):
        submenu.deleteLater()
    menu.clear()


def number_field(value=None):
    """Return a field for a number that uses a decimal point in every locale."""
    field = QLineEdit("" if value is None else f"{value:.12g}")
    validator = QDoubleValidator(field)
    validator.setLocale(QLocale.c())
    field.setValidator(validator)
    field.setMaximumWidth(FIELD_WIDTH)
    field.setCursorPosition(0)  # Show the start of a long number.
    return field


class NumberForm(QWidget):
    """The form shows rows of number fields for a menu, one per (text, value) pair.

    When the user edits a field, *apply* is called with the numbers from all
    fields.
    """

    def __init__(self, rows, apply):
        super().__init__()
        QFormLayout(self).setContentsMargins(10, 4, 10, 4)
        self.apply, self.fields = apply, []
        for text, value in rows:
            self.fields.append(number_field(value))
            self.fields[-1].editingFinished.connect(self._edited)
            self.layout().addRow(text, self.fields[-1])

    def _edited(self):
        if (typed := numbers(self.fields)) is not None:
            self.apply(*typed)

    def show_values(self, values):
        """Show *values*, except in a field that has focus."""
        for field, value in zip(self.fields, values, strict=True):
            if not field.hasFocus():
                field.setText(f"{value:.12g}")  # Epoch seconds have 10 digits.
                field.setCursorPosition(0)


def add_widget(menu, widget):
    action = QWidgetAction(menu)
    action.setDefaultWidget(widget)
    menu.addAction(action)


def elide_words(metrics, text, width):
    """Cut words off the end of *text* and add "…" until it fits *width*."""
    words = text.split(" ")
    while len(words) > 1 and metrics.horizontalAdvance(text) > width:
        words.pop()
        text = " ".join([*words, "…"])
    return text


# Every plot menu has its entries in this order, with a separator between the
# groups. A plot leaves out the entries it does not have. Owners add entries
# under these keys.
MENU_ORDER = (
    ("Show",),
    ("Log scale", "Colours", "Profiles", "Corrections", "Curves"),
    ("Measure", "ROIs"),
    ("Freeze", "Reset zoom"),
    ("Only this plot", "Hide", "Layout"),
    ("Presets", "Save plot", "Attach to electronic log"),
)


def fill_menu(menu, entries):
    """Add *entries* to *menu* in the order of MENU_ORDER.

    *entries* maps a key from MENU_ORDER to a function add(menu) or to the
    arguments of `check_action`.
    """
    for group in MENU_ORDER:
        adds = [entries[key] for key in group if key in entries]
        if adds and not menu.isEmpty():
            menu.addSeparator()
        for add in adds:
            add(menu) if callable(add) else check_action(menu, *add)


def submenu(title, fill):
    """Return an entry that adds a submenu called *title* and fills it with *fill*."""

    def add(menu):
        sub = menu.addMenu(title)
        sub.setToolTipsVisible(True)
        fill(sub)

    return add


def check_action(menu, text, checked, slot, tip=""):
    """Add a checkable action that calls *slot* with the new state."""
    action = menu.addAction(text)
    action.setCheckable(True)
    action.setChecked(checked)
    action.triggered.connect(slot)
    action.setToolTip(tip or text)
    return action


def radio_entries(menu, choices, current, slot):
    """Add an exclusive checkable entry for each value and text in *choices*.

    The entry for *current* is checked. Choosing an entry calls *slot* with
    the value of that entry.
    """
    group = QActionGroup(menu)
    for value, text in choices.items():
        on = value == current
        group.addAction(check_action(menu, text, on, lambda _, v=value: slot(v)))


class DataShape:
    """Keep an aspect-locked view box in the shape of its data.

    Extra layout margins on the layout *around* the plot centre the view box,
    so there is no empty range around the data. Items along the edges of the
    view box such as the profiles then line up with the data.
    """

    def __init__(self, plot, around):
        self.plot, self.around = plot, around
        # The aspect is the width over the height of the data. None fills the space.
        self.aspect = None
        self.base = self.around.layout.getContentsMargins()
        self.extra = (0.0, 0.0)
        plot.vb.sigResized.connect(self.fit)
        self.around.geometryChanged.connect(self.fit)
        # The extra margins must not keep the plot wider than a narrow cell.
        self.around.setMinimumSize(1, 1)

    def set_aspect(self, aspect):
        if aspect != self.aspect:
            self.aspect = aspect
            self.fit()
            settle_layout(self.around)

    def fit(self):
        vb, size = self.plot.vb, self.around.size()
        need = self.around.layout.effectiveSizeHint(Qt.SizeHint.MinimumSize)
        width = vb.width() + self.extra[0] - max(0.0, need.width() - size.width())
        height = vb.height() + self.extra[1] - max(0.0, need.height() - size.height())
        extra = (0.0, 0.0)
        if self.aspect and width > 0 and height > 0:
            if width / height > self.aspect:
                extra = (width - height * self.aspect, 0.0)
            else:
                extra = (0.0, height - width / self.aspect)
        if max(abs(a - b) for a, b in zip(extra, self.extra, strict=True)) < 1:
            return  # New margins resize the view box again, which would loop.
        self.extra = extra
        left, top, right, bottom = self.base
        self.around.layout.setContentsMargins(
            left + extra[0] / 2,
            top + extra[1] / 2,
            right + extra[0] / 2,
            bottom + extra[1] / 2,
        )


def settle_layout(plot):
    """Lay out *plot* right away so Qt does not paint items in old places.

    The loop is needed because one pass can trigger another through
    `DataShape`.
    """
    for _ in range(4):
        if plot.layout.isActivated():
            return
        plot.layout.activate()


class Title(pg.LabelItem):
    """The title line shows a bold name and parts of (text, colour, kept).

    When the line is too narrow, the last parts that are not kept are left out
    first. Then the name is shortened down to 12 letters, and after that the
    kept parts are shortened. A note is cut between words and a number is
    never cut. Each part keeps the width of its widest numbers so the parts
    after it do not move. The tooltip shows all parts and *hints*. With *menu*
    set, a click on the name emits ``menu_requested`` with the screen position
    below the name.
    """

    menu_requested = pyqtSignal(object)

    def __init__(self, menu=False):
        super().__init__(justify="left")
        self.menu = menu
        self.bold = QFontMetricsF(scaled_font(TITLE_SCALE, bold=True))
        self.plain = QFontMetricsF(scaled_font(TITLE_SCALE))
        self.line_height = round(self.bold.height() * 1.25)
        fix_label_size(self, self.line_height)
        self.name, self.parts, self.hints = "", [], ()
        # This maps each part with its numbers masked to its width in pixels.
        self.rooms = {}
        self.name_end = 0.0  # The name and the menu marker end at this x.
        self.geometryChanged.connect(self._fit)

    def set_parts(self, name, parts=(), hints=()):
        if name != self.name:
            self.rooms = {}
        self.name, self.parts, self.hints = name or "", list(parts), hints
        height = self.line_height if self.name or self.parts else 0
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.setVisible(bool(height))
        self._fit()

    def _room(self, text):
        """Return the width for a part.

        The width only shrinks when the part got narrower by more than two
        digits.
        """
        width = self.plain.horizontalAdvance(text)
        key = NUMBER.sub("#", text)
        room = self.rooms.get(key, 0.0)
        if width > room or width < room - self.plain.horizontalAdvance("00"):
            room = self.rooms[key] = width
        return room

    def _padded(self, text, color):
        pad = self._room(text) - self.plain.horizontalAdvance(text)
        space = self.plain.horizontalAdvance("\u00a0")
        filler = f"<span style='letter-spacing:{pad - space:.2f}px'>&nbsp;</span>"
        return f"<span style='color:{color or '#222'}'>{html.escape(text)}</span>" + (
            filler if pad > 0.1 else ""
        )

    def _fit(self):
        marker = MENU_MARKER if self.menu and self.name else ""
        width = self.geometry().width() or 1e6  # The width is 0 before layout.
        width -= 8 + self.plain.horizontalAdvance(marker)
        sep = self.plain.horizontalAdvance(" · ")
        # The name tells plots apart, so it never gets shorter than 12 letters.
        name = self.name
        floor = name if len(name) <= 12 else f"{name[:6]}…{name[-5:]}"

        def wide(name, parts):
            return self.bold.horizontalAdvance(name) + sum(
                sep + self._room(text) for text, *_p in parts
            )

        # Shorten the name to the room that the parts leave.
        def shortened(parts):
            name = self.bold.elidedText(
                self.name, Qt.TextElideMode.ElideMiddle, width - wide("", parts)
            )
            return name if len(name) >= len(floor) else floor

        kept = list(self.parts)
        while wide(self.name, kept) > width and not all(p[2] for p in kept):
            kept.pop(max(i for i, p in enumerate(kept) if not p[2]))
        name = shortened(kept)
        if wide(name, kept) > width:  # Keep parts whole or cut a note at a word.
            room, fitted = width - self.bold.horizontalAdvance(name) - sep, []
            for text, color, keep in kept:
                short = (
                    text if NUMBER.search(text) else elide_words(self.plain, text, room)
                )
                if self._room(short) > room:
                    continue  # Leave this part out because the age may still fit.
                fitted.append((short, color, keep))
                room -= sep + self._room(short)
                if short != text:
                    break
            kept = fitted
            name = shortened(kept)
        self.name_end = (
            self.item.pos().x()
            + self.item.document().documentMargin()
            + self.bold.horizontalAdvance(name + marker)
        )
        pieces = [
            f"<b>{html.escape(name)}</b><span style='color:{MUTED}'>{marker}</span>"
        ] * bool(name)
        pieces += [self._padded(text, color) for text, color, _keep in kept]
        self.setText(
            f"<span style='color:{MUTED}'> · </span>".join(pieces),
            size=css_size(TITLE_SCALE),
            color="#222",
        )
        self.setToolTip(
            "\n".join([self.name, *(p[0] for p in self.parts), *self.hints])
        )

    def _on_name(self, pos):
        return self.menu and bool(self.name) and pos.x() <= self.name_end + 4

    def hoverEvent(self, ev):
        if not ev.isExit() and self._on_name(ev.pos()):
            ev.acceptClicks(Qt.MouseButton.LeftButton)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    def mouseClickEvent(self, ev):
        right = self.menu and ev.button() == Qt.MouseButton.RightButton
        if not right and not self._on_name(ev.pos()):
            ev.ignore()
            return
        ev.accept()
        view = self.getViewWidget()
        below = self.mapToScene(QPointF(self.item.pos().x(), self.height()))
        self.menu_requested.emit(
            view.mapToGlobal(view.mapFromScene(below)) if view else QPoint()
        )


class PlotMenu(QObject):
    """The menu of a plot, which replaces the pyqtgraph menus.

    The menu opens on a right-click on the plot. Each time it opens, *fill*
    gets the entries "Reset zoom" and "Save plot…" and adds its own entries as
    described in `fill_menu`. "Reset zoom" calls *reset*.
    """

    def __init__(self, plot, fill, reset):
        super().__init__(plot)
        self.plot, self.fill, self.reset = plot, fill, reset
        self.menu = QMenu()
        self.menu.setToolTipsVisible(True)
        self.menu.aboutToShow.connect(self.refill)
        # A QMenu cannot have a plot item as its parent, so the menu is deleted
        # together with the plot here.
        plot.destroyed.connect(self.menu.deleteLater)
        plot.vb.raiseContextMenu = lambda ev: self.open(ev.screenPos().toPoint())

    def open(self, pos):
        self.menu.popup(pos)

    def refill(self):
        clear_menu(self.menu)
        entries = {
            "Reset zoom": lambda m: m.addAction("Reset zoom", lambda: self.reset()),
            "Save plot": lambda m: m.addAction("Save plot…", self.save),
        }
        self.fill(entries)
        fill_menu(self.menu, entries)

    def save(self):
        view = self.plot.getViewWidget()
        save_plot_dialog(view, view)


def _rows_table(where, rows, room):
    """Return *where* and the *rows* of a `HoverBox` as an HTML table.

    When there are more than *room* rows, the table leaves out the rows
    farthest from the pointer and says how many it left out.
    """
    near = sorted(range(len(rows)), key=lambda k: rows[k][3])
    shown = sorted(near[: room - 1]) if len(rows) > room else range(len(rows))
    cells = [f"<tr><td colspan=3 style='color:{MUTED}'>{html.escape(where)}</td></tr>"]
    for k in shown:
        color, name, value, _distance = rows[k]
        swatch = "" if color is None else f"<span style='color:{color.name()}'>■</span>"
        name, value = html.escape(name), html.escape(value)
        if k == near[0] and len(rows) > 1:
            name, value = f"<b>{name}</b>", f"<b>{value}</b>"
        cells.append(
            f"<tr><td>{swatch}</td><td>{name}</td><td align=right>{value}</td></tr>"
        )
    if more := len(rows) - len(shown):
        cells.append(f"<tr><td colspan=3 style='color:{MUTED}'>+ {more} more</td></tr>")
    return f"<table cellspacing=0 cellpadding=1>{''.join(cells)}</table>"


class HoverBox(pg.GraphicsObject):
    """A box next to the pointer that shows the values under the pointer.

    The first row says where the pointer is, and then each curve gets a row
    with colour, name and value. The curve nearest to the pointer is bold.
    The box stays inside an area of its parent. It moves to the left of the
    pointer when there is no room on the right and stays there while it fits.
    If neither side fits, the box goes above or below the pointer but never
    covers it. When there are too many rows, the curves farthest from the
    pointer are left out.
    """

    GAP = 14  # The gap between the pointer and the box is in pixels.

    def __init__(self, parent):
        super().__init__(parent)
        self.setZValue(1e9)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label = QGraphicsTextItem(self)
        self.label.setFont(scaled_font(TICK_SCALE))
        self.line_height = QFontMetricsF(self.label.font()).height() + 2
        self.left = False  # This is True while the box is left of the pointer.
        self.hide()

    def boundingRect(self):
        return self.label.boundingRect()

    def paint(self, painter, *_args):
        painter.setPen(pg.mkPen(BOX_EDGE))
        painter.setBrush(pg.mkBrush(BOX_FILL))
        painter.drawRoundedRect(self.boundingRect(), 3, 3)

    def show_rows(self, where, rows, at, area):
        """Show *where* and *rows* next to the point *at* inside *area*.

        Each row is (colour, name, value, distance in pixels). *at* and *area*
        are in the coordinates of the parent. The box hides when there are no
        rows and while a drag draws or moves something.
        """
        if not rows or QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            self.hide()
            return
        room = max(1, int(area.height() // self.line_height) - 2)
        self.prepareGeometryChange()
        self.label.setHtml(_rows_table(where, rows, room))
        self._move_beside(at, area)
        self.show()

    def _move_beside(self, at, area):
        box = self.boundingRect()
        x, y = at.x() + self.GAP, at.y() + self.GAP
        left = at.x() - self.GAP - box.width()
        # Once the box is on the left, it stays there while it fits so it does
        # not jump.
        if x + box.width() > area.right() or self.left and left >= area.left():
            x = left
        self.left = x == left
        if y + box.height() > area.bottom() and at.y() > area.center().y():
            y = at.y() - self.GAP - box.height()
        if x >= area.left():  # Beside the pointer the box can be at any height.
            y = max(area.top(), min(y, area.bottom() - box.height()))
        self.setPos(max(area.left(), x), y)

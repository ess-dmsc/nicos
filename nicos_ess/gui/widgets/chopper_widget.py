"""The chopper discs, drawn as seen from the moderator looking towards the sample.

Disc angles (chopper_math) and Qt's arcs and polar lines share one convention:
degrees anticlockwise from 3 o'clock on the screen. A disc point at angle ``a`` is
drawn at ``rotation + a``.
"""

import math

from nicos.guisupport.qt import (
    QColor,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineF,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPointF,
    QRectF,
    Qt,
    QWidget,
    pyqtSignal,
)
from nicos_ess.devices.chopper_math import (
    check_geometry,
    clockwise,
    guide_angle,
    is_chopper_moving,
    parked_rotation_deg,
    phase_deg,
    spinning_rotation_deg,
)

BLADE = QColor(Qt.GlobalColor.darkGray)
COATING = QColor(Qt.GlobalColor.black)
ROTATING = QColor(30, 255, 30)
PARKED = QColor(Qt.GlobalColor.gray)
GUIDE = QColor(Qt.GlobalColor.blue)
WAITING = QColor(190, 190, 190, 130)

LIVE_VALUES = ("speed", "total_delay", "park_angle")


def polar(center: QPointF, radius: float, angle_deg: float) -> QPointF:
    return QLineF.fromPolar(radius, angle_deg).translated(center).p2()


def square(center: QPointF, radius: float) -> QRectF:
    return QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius)


def disc_material(center, inner, outer, slit_edges, rotation) -> QPainterPath:
    """The ring between the radii minus one wedge per opening."""
    ring = QPainterPath()
    ring.addEllipse(center, outer, outer)
    hole = QPainterPath()
    hole.addEllipse(center, inner, inner)
    ring = ring.subtracted(hole)
    box = square(center, outer + 1.0)
    for start, end in slit_edges:
        sweep = (end - start) % 360.0 or (360.0 if end != start else 0.0)
        wedge = QPainterPath(center)
        wedge.arcTo(box, rotation + start, sweep)
        wedge.closeSubpath()
        ring = ring.subtracted(wedge)
    return ring


def spin_arc(guide: float, turns_clockwise: bool, span: float = 72.0):
    """Start angle and sweep of the spin arrow, centred on the beam guide."""
    if turns_clockwise:
        return guide + span / 2.0, -span
    return guide - span / 2.0, span


def _swatch(size: int, draw) -> QLabel:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    draw(painter, size)
    painter.end()
    label = QLabel()
    label.setPixmap(pixmap)
    return label


class ChopperLegendWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 5, 9, 5)
        size = max(9, self.fontMetrics().height())

        def blade(painter, s):
            painter.fillRect(0, 0, s, s, BLADE)
            painter.fillRect(0, s // 4, s, s // 2, COATING)

        def guide(painter, s):
            painter.setPen(QPen(GUIDE, max(2, s // 4)))
            painter.drawLine(s // 2, 0, s // 2, s)

        def fill(colour):
            def draw(painter, s):
                painter.setPen(COATING)
                painter.setBrush(colour)
                painter.drawRect(0, 0, s - 1, s - 1)

            return draw

        items = (
            (blade, "Coated blade"),
            (guide, "Beam guide"),
            (fill(ROTATING), "Rotating"),
            (fill(PARKED), "Parked"),
        )
        for draw, text in items:
            layout.addWidget(_swatch(size, draw))
            layout.addWidget(QLabel(text))
            layout.addSpacing(11)


class ChopperWidget(QWidget):
    onChopperSelected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self.chopper_data = []
        self._selected_chopper = None
        self._show_guide_line = True

    def get_selected_chopper(self):
        return self._selected_chopper

    def update_chopper_data(self, chopper_data):
        """Show these choppers in beam order; live values already shown are kept.

        Discs without a distance from the moderator come last, in the given order.
        """
        live = {
            c["chopper"]: {k: c.get(k) for k in LIVE_VALUES} for c in self.chopper_data
        }
        chopper_data = sorted(
            chopper_data,
            key=lambda c: (c.get("distance") is None, c.get("distance") or 0.0),
        )
        for chopper in chopper_data:
            check_geometry(chopper)
            chopper["guide_angle"] = guide_angle(chopper)
            chopper.update(live.get(chopper["chopper"], {}))
        self.chopper_data = chopper_data
        self.update()

    def clear(self):
        self.chopper_data = []
        self._selected_chopper = None
        self.update()

    def set_value(self, chopper_name, key, value):
        """Set a live value (LIVE_VALUES): None while it is unknown."""
        for chopper in self.chopper_data:
            if chopper["chopper"] == chopper_name:
                chopper[key] = None if value is None else float(value)
                self.update()

    def rotation(self, chopper: dict) -> float | None:
        """Screen angle of the disc's angle 0 (its TDC reference), or None while waiting."""
        speed = chopper.get("speed")
        if speed is None:
            return None
        if is_chopper_moving(speed):
            delay = chopper.get("total_delay")
            if delay is None:
                return None
            return spinning_rotation_deg(chopper, phase_deg(delay, speed), speed)
        reading = chopper.get("park_angle")
        if reading is None and chopper.get("resolver_sign") is not None:
            return None
        return parked_rotation_deg(chopper, reading)

    def layout_discs(self):
        """Centres and radius of the discs, in a grid that suits the aspect ratio."""
        count, width, height = len(self.chopper_data), self.width(), self.height()
        if not count or not width or not height:
            return [], 0.0
        cols = min(
            range(1, count + 1),
            key=lambda c: abs(c / math.ceil(count / c) - width / height),
        )
        rows = math.ceil(count / cols)
        pad_w, pad_h = width / cols / 6, height / rows / 6
        cell_w = (width - (cols + 1) * pad_w) / cols
        cell_h = (height - (rows + 1) * pad_h) / rows
        centres = []
        for index in range(count):
            row, col = divmod(index, cols)
            centres.append(
                QPointF(
                    pad_w + col * (cell_w + pad_w) + (cell_w + pad_w) / 2,
                    pad_h + row * (cell_h + pad_h) + (cell_h + pad_h) / 2,
                )
            )
        return centres, min(cell_w, cell_h) / 2

    def mousePressEvent(self, event):
        centres, radius = self.layout_discs()
        self._selected_chopper = None
        for chopper, centre in zip(self.chopper_data, centres, strict=False):
            if QLineF(centre, QPointF(event.pos())).length() <= radius:
                self._selected_chopper = chopper["chopper"]
        self.onChopperSelected.emit(self._selected_chopper)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        centres, radius = self.layout_discs()
        for chopper, centre in zip(self.chopper_data, centres, strict=False):
            selected = chopper["chopper"] == self._selected_chopper
            outline = QPen(GUIDE, 2) if selected else QPen(COATING, 1)
            rotation = self.rotation(chopper)
            if rotation is None:
                painter.setPen(outline)
                painter.setBrush(WAITING)
                painter.drawEllipse(centre, radius * 0.7, radius * 0.7)
                self._draw_labels(
                    painter, centre, radius, chopper, selected, ["Waiting"]
                )
                continue

            speed = chopper["speed"]
            moving = is_chopper_moving(speed)
            edges = chopper["slit_edges"]
            inner = radius * 0.7
            painter.fillPath(
                disc_material(centre, inner, radius, edges, rotation), BLADE
            )
            painter.fillPath(
                disc_material(centre, radius * 0.75, radius * 0.95, edges, rotation),
                COATING,
            )
            painter.setPen(outline)
            painter.setBrush(ROTATING if moving else PARKED)
            painter.drawEllipse(centre, inner, inner)

            if self._show_guide_line:
                painter.setPen(QPen(GUIDE, 4))
                painter.drawLine(
                    centre, polar(centre, radius * 1.1, chopper["guide_angle"])
                )
            if moving:
                self._draw_spin_arrow(
                    painter,
                    centre,
                    radius * 0.55,
                    chopper["guide_angle"],
                    clockwise(chopper, speed),
                )

            park_angle = chopper.get("park_angle")
            parked = not moving and park_angle is not None
            value = f"{park_angle:.3f}°" if parked else f"{speed:.3f} Hz"
            status = "Rotating" if moving else "Parked"
            self._draw_labels(
                painter, centre, radius, chopper, selected, [value, status]
            )

    def _draw_spin_arrow(self, painter, centre, radius, guide, turns_clockwise):
        start, sweep = spin_arc(guide, turns_clockwise)
        box = square(centre, radius)
        path = QPainterPath()
        path.arcMoveTo(box, start)
        path.arcTo(box, start, sweep)
        tip, heading = path.pointAtPercent(1.0), path.angleAtPercent(1.0)
        head = max(6.0, radius * 0.25)
        for side in (-28.0, 28.0):
            path.moveTo(tip)
            path.lineTo(polar(tip, head, heading + 180.0 + side))
        pen = QPen(QColor(15, 15, 15, 210), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.strokePath(path, pen)

    def _label_rects(self, chopper, centre, radius, count, row_height):
        """The name outside the disc, the other rows inside; both away from the beam."""
        width = radius * 3.0
        left = centre.x() - radius * 1.5
        if chopper["guide_angle"] == 270.0:  # beam down: text upwards
            tops = [centre.y() - radius - 5 - row_height]
            tops += [centre.y() - k * row_height for k in range(1, count)]
        else:
            tops = [centre.y() + radius + 5]
            tops += [centre.y() + (k - 1) * row_height for k in range(1, count)]
        return [QRectF(left, top, width, row_height) for top in tops]

    def _draw_labels(self, painter, centre, radius, chopper, selected, rows):
        font = painter.font()
        font.setPointSize(max(1, int(radius / 8)))
        painter.setFont(font)
        rows = [chopper["chopper"], *rows]
        rects = self._label_rects(
            chopper, centre, radius, len(rows), painter.fontMetrics().height()
        )
        for index, (rect, text) in enumerate(zip(rects, rows, strict=True)):
            painter.setPen(GUIDE if selected and index == 0 else COATING)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

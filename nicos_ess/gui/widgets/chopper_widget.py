import json
import math
import sys
from enum import Enum
from typing import Optional

from nicos.guisupport.qt import (
    QApplication,
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPointF,
    QPolygonF,
    QRectF,
    Qt,
    QWidget,
    pyqtSignal,
)
from nicos_ess.gui.widgets.chopper_math import (
    build_rotation_model,
    has_canonical_inputs,
    parked_rotation_deg,
    runtime_phase_sign,
    spinning_rotation_deg,
    wrap360,
)


class Colors(Enum):
    GREEN = QColor(30, 255, 30, 255)
    GRAY = Qt.GlobalColor.gray
    BLUE = Qt.GlobalColor.blue
    DARK_GRAY = Qt.GlobalColor.darkGray
    BLACK = Qt.GlobalColor.black


class ChopperWidget(QWidget):
    onChopperSelected = pyqtSignal(str)

    GUIDE_DIRS = {"RIGHT": 0.0, "UP": 90.0, "LEFT": 180.0, "DOWN": 270.0}

    def __init__(self, parent=None, guide_pos="UP"):
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self.chopper_data = []
        self.angles = {}
        self._selected_chopper = None
        self._guide_pos = guide_pos
        self._guide_angle_deg = self._to_guide_deg(guide_pos)
        self._detailed_view = False
        self._show_guide_line = True

        self._default_rotation_offset = self._guide_angle_deg

    def get_selected_chopper(self):
        return self._selected_chopper

    def mousePressEvent(self, event):
        """Handle mouse click events to select a chopper."""
        click_pos = event.pos()
        positions, chopper_radius = self.calculate_positions(len(self.chopper_data))

        for i, center in enumerate(positions):
            distance = math.sqrt(
                (center.x() - click_pos.x()) ** 2 + (center.y() - click_pos.y()) ** 2
            )
            if distance <= chopper_radius:
                self._selected_chopper = self.chopper_data[i]["chopper"]
                self.onChopperSelected.emit(self._selected_chopper)
                self.update()
                return

        self._selected_chopper = None
        self.onChopperSelected.emit(None)
        self.update()

    def _to_guide_deg(self, pos) -> float:
        if isinstance(pos, (int, float)):
            return float(pos) % 360.0
        key = str(pos).upper()
        if key not in self.GUIDE_DIRS:
            raise ValueError(f"Invalid guide position: {pos!r}")
        return self.GUIDE_DIRS[key]

    def set_guide_position(self, pos) -> None:
        new_deg = self._to_guide_deg(pos)
        self._guide_pos = pos
        self._guide_angle_deg = new_deg
        self._default_rotation_offset = new_deg
        self.update()

    def set_detailed_view(self, enabled: bool) -> None:
        self._detailed_view = bool(enabled)
        self.update()

    def is_detailed_view_enabled(self) -> bool:
        return self._detailed_view

    def set_show_guide_line(self, enabled: bool) -> None:
        self._show_guide_line = bool(enabled)
        self.update()

    def _wrap360(self, x: float) -> float:
        return wrap360(x)

    def set_chopper_angle(self, chopper_name, angle):
        # Store raw device angle; mode-specific direction/offset handling happens
        # in paint-time bookkeeping based on speed and canonical metadata.
        for i, chopper in enumerate(self.chopper_data):
            if chopper["chopper"] == chopper_name:
                self.angles[i] = self._wrap360(float(angle))
        self.update()

    def set_chopper_speed(self, chopper_name, speed):
        try:
            for i, chopper in enumerate(self.chopper_data):
                if chopper["chopper"] == chopper_name:
                    chopper["speed"] = speed
                    self.update()
                    return
        except KeyError:
            pass

    def set_chopper_park_angle(self, chopper_name, angle):
        try:
            for i, chopper in enumerate(self.chopper_data):
                if chopper["chopper"] == chopper_name:
                    chopper["parking_angle"] = angle
                    self.update()
                    return
        except KeyError:
            pass

    def _canonical_rotation_base(
        self, chopper: dict, raw_angle: float, speed_hz: Optional[float], moving: bool
    ) -> float:
        if not has_canonical_inputs(chopper):
            raise ValueError(
                f"Chopper {chopper.get('chopper')!r} missing canonical bookkeeping inputs"
            )
        model = build_rotation_model(chopper)
        if moving:
            return spinning_rotation_deg(
                raw_angle,
                speed_hz,
                model.spin_offset_deg,
                model.base_spin_direction,
                model.phase_reference_sign,
            )
        return parked_rotation_deg(
            raw_angle,
            model.resolver_offset_deg,
            model.base_spin_direction,
            model.phase_reference_sign,
        )

    def _rotation_base_deg(
        self, chopper: dict, raw_angle: float, speed_hz: Optional[float], moving: bool
    ) -> float:
        return self._canonical_rotation_base(chopper, raw_angle, speed_hz, moving)

    def get_rotation_angle_for_chopper(
        self, chopper_name: str, include_guide: bool = False
    ) -> Optional[float]:
        """Return current computed draw rotation for one chopper.

        This keeps tests focused on the widget's own bookkeeping without
        requiring panel/client setup.
        """
        for i, chopper in enumerate(self.chopper_data):
            if chopper["chopper"] != chopper_name:
                continue
            speed_hz = chopper.get("speed", 0.0)
            moving = speed_hz is not None and abs(float(speed_hz)) >= 2
            raw_angle = float(self.angles.get(i, 0.0))
            try:
                base_rotation = self._rotation_base_deg(
                    chopper, raw_angle, speed_hz, moving
                )
            except ValueError:
                return None
            if include_guide:
                # Geometry conversion from engineering CW+ to Qt math-CCW.
                return self._wrap360(base_rotation + self._default_rotation_offset)
            return self._wrap360(base_rotation)
        return None

    def _tdc_marker_angle_for_chopper(self, chopper: dict) -> Optional[float]:
        if not has_canonical_inputs(chopper):
            return None
        try:
            model = build_rotation_model(chopper)
        except ValueError:
            return None
        tdc_resolver = float(chopper["tdc_resolver_position"])
        tdc_base_rotation = parked_rotation_deg(
            tdc_resolver,
            model.resolver_offset_deg,
            model.base_spin_direction,
            model.phase_reference_sign,
        )
        tdc_qt_rotation = self._wrap360(
            tdc_base_rotation + self._default_rotation_offset
        )
        # Opening-center world angle at TDC reference.
        return self._wrap360(-model.parked_opening_center_deg + tdc_qt_rotation)

    def get_tdc_marker_angle_for_chopper(self, chopper_name: str) -> Optional[float]:
        for chopper in self.chopper_data:
            if chopper["chopper"] == chopper_name:
                return self._tdc_marker_angle_for_chopper(chopper)
        return None

    def _spin_direction_sign(
        self, chopper: dict, speed_hz: Optional[float]
    ) -> Optional[int]:
        if not has_canonical_inputs(chopper):
            return None
        try:
            model = build_rotation_model(chopper)
        except ValueError:
            return None
        # runtime_phase_sign is defined so positive speed is rendered as
        # clockwise in the UI across motor-side conventions.
        return runtime_phase_sign(
            speed_hz, model.base_spin_direction, model.phase_reference_sign
        )

    def get_spin_direction_sign_for_chopper(self, chopper_name: str) -> Optional[int]:
        for chopper in self.chopper_data:
            if chopper["chopper"] != chopper_name:
                continue
            speed_hz = chopper.get("speed", 0.0)
            return self._spin_direction_sign(chopper, speed_hz)
        return None

    def _spin_indicator_arc_angles(
        self, spin_sign: int, span_deg: float = 72.0
    ) -> tuple[float, float]:
        half_span = span_deg / 2.0
        if spin_sign >= 0:
            start = self._guide_angle_deg + half_span
            end = self._guide_angle_deg - half_span
        else:
            start = self._guide_angle_deg - half_span
            end = self._guide_angle_deg + half_span
        return self._wrap360(start), self._wrap360(end)

    def _point_on_circle(
        self, center: QPointF, radius: float, angle_deg: float
    ) -> QPointF:
        theta = math.radians(angle_deg)
        return QPointF(
            center.x() + radius * math.cos(theta),
            center.y() - radius * math.sin(theta),
        )

    def _draw_arrow_head(
        self, painter: QPainter, prev_point: QPointF, tip_point: QPointF, size: float
    ) -> None:
        vx = tip_point.x() - prev_point.x()
        vy = tip_point.y() - prev_point.y()
        norm = math.hypot(vx, vy)
        if norm < 1e-9:
            return
        ux, uy = vx / norm, vy / norm
        bx, by = -ux, -uy

        alpha = math.radians(28.0)
        cos_a = math.cos(alpha)
        sin_a = math.sin(alpha)

        ldx = bx * cos_a - by * sin_a
        ldy = bx * sin_a + by * cos_a
        rdx = bx * cos_a + by * sin_a
        rdy = -bx * sin_a + by * cos_a

        left = QPointF(tip_point.x() + size * ldx, tip_point.y() + size * ldy)
        right = QPointF(tip_point.x() + size * rdx, tip_point.y() + size * rdy)
        painter.drawLine(tip_point, left)
        painter.drawLine(tip_point, right)

    def _draw_spin_direction_indicator(
        self, painter: QPainter, center: QPointF, radius: float, spin_sign: int
    ) -> None:
        start_deg, end_deg = self._spin_indicator_arc_angles(spin_sign)
        # Avoid wrap discontinuity during interpolation.
        if end_deg - start_deg > 180.0:
            end_deg -= 360.0
        elif start_deg - end_deg > 180.0:
            end_deg += 360.0

        nsteps = 22
        points = []
        for i in range(nsteps + 1):
            t = i / nsteps
            angle = start_deg + t * (end_deg - start_deg)
            points.append(self._point_on_circle(center, radius, angle))

        painter.save()
        pen = QPen(QColor(15, 15, 15, 210), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.drawPath(path)

        self._draw_arrow_head(
            painter,
            points[-2],
            points[-1],
            size=max(6.0, radius * 0.14),
        )
        painter.restore()

    def resizeEvent(self, event):
        self.update()

    def paintEvent(self, event):
        """Handle the drawing of the choppers."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        positions, chopper_radius = self.calculate_positions(len(self.chopper_data))
        slit_height = chopper_radius * 0.3
        line_length = chopper_radius * 1.1

        for i, chopper in enumerate(self.chopper_data):
            radius = chopper_radius
            slit_edges = chopper["slit_edges"]
            current_speed = chopper.get("speed", 0.0)
            parking_angle = chopper.get("parking_angle", None)
            center = positions[i]

            is_selected = self._selected_chopper == chopper["chopper"]
            is_moving = current_speed is not None and abs(float(current_speed)) >= 2
            raw_angle = float(self.angles.get(i, 0.0))
            try:
                base_rotation = self._rotation_base_deg(
                    chopper, raw_angle, current_speed, is_moving
                )
            except ValueError:
                continue
            # Convert canonical engineering CW+ rotation to Qt math-CCW.
            angle = self._wrap360(base_rotation + self._default_rotation_offset)

            self.draw_chopper(
                painter,
                center,
                radius,
                slit_edges,
                slit_height,
                angle,
                is_selected,
                is_moving,
            )
            if self._detailed_view:
                self._draw_chopper_details(painter, center, radius, chopper)

            if self._show_guide_line:
                painter.setPen(QPen(Colors.BLUE.value, 4))
                # line_x = center.x()
                # line_y = center.y() - line_length
                theta = math.radians(
                    self._guide_angle_deg
                )  # 0=right, 90=up, 180=left, 270=down
                line_x = center.x() + line_length * math.cos(theta)
                line_y = center.y() - line_length * math.sin(theta)
                painter.drawLine(center, QPointF(line_x, line_y))
            if is_moving:
                spin_sign = self._spin_direction_sign(chopper, current_speed)
                if spin_sign is not None:
                    self._draw_spin_direction_indicator(
                        painter, center, line_length * 0.5, spin_sign
                    )

            text_direction = -1 if self._guide_angle_deg == 270 else 1

            chopper_name = chopper["chopper"]
            if is_selected:
                painter.setPen(Colors.BLUE.value)
            else:
                painter.setPen(Colors.BLACK.value)
            font = painter.font()
            font.setPointSize(int(radius / 8))
            painter.setFont(font)

            fm = painter.fontMetrics()
            text_height = fm.height()

            text_rect = QRectF(
                center.x() - radius * 1.5,
                center.y() + (radius + 5) * text_direction,
                radius * 3.0,
                text_height * text_direction,
            )

            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, chopper_name)

            if current_speed is None:
                continue

            painter.setPen(Colors.BLACK.value)
            if not is_moving and parking_angle is not None:
                value_text = f"{parking_angle:.3f}°"
            else:
                value_text = f"{current_speed:.3f} Hz"
            value_rect = QRectF(
                center.x() - radius * 1.5,
                center.y() + text_height * text_direction,
                radius * 3.0,
                text_height * text_direction,
            )
            painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, value_text)

            status_text = "Rotating" if is_moving else "Parked"
            status_rect = QRectF(
                center.x() - radius * 1.5,
                center.y() + (2 * text_height) * text_direction,
                radius * 3.0,
                text_height * text_direction,
            )
            painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, status_text)

        self.draw_legend(painter, chopper_radius)

    def _draw_chopper_details(
        self, painter: QPainter, center: QPointF, radius: float, chopper: dict
    ) -> None:
        motor_position = str(chopper.get("motor_position", "")).strip().lower()
        motor_alpha = 220 if motor_position == "upstream" else 95

        hub_radius = radius * 0.24
        spindle_radius = radius * 0.08
        housing_color = QColor(90, 90, 90, motor_alpha)
        spindle_color = QColor(40, 40, 40, 220)

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(housing_color))
        painter.drawEllipse(center, hub_radius, hub_radius)
        painter.setBrush(QBrush(spindle_color))
        painter.drawEllipse(center, spindle_radius, spindle_radius)

        tdc_angle = self._tdc_marker_angle_for_chopper(chopper)
        if tdc_angle is not None:
            theta = math.radians(tdc_angle)
            p_inner = QPointF(
                center.x() + (radius * 0.74) * math.cos(theta),
                center.y() - (radius * 0.74) * math.sin(theta),
            )
            p_outer = QPointF(
                center.x() + (radius * 1.02) * math.cos(theta),
                center.y() - (radius * 1.02) * math.sin(theta),
            )
            painter.setPen(QPen(QColor(210, 45, 45, 210), 2, Qt.PenStyle.DashLine))
            painter.drawLine(p_inner, p_outer)
            painter.setPen(QPen(QColor(210, 45, 45, 210), 1))
            label_pos = QPointF(
                center.x() + (radius * 1.08) * math.cos(theta),
                center.y() - (radius * 1.08) * math.sin(theta),
            )
            painter.drawText(label_pos, "TDC")
        painter.restore()

    def draw_legend(self, painter: QPainter, ref_radius: float) -> None:
        painter.save()

        icon = max(12, int(ref_radius * 0.20))
        gap_y = 4
        gap_x = 6
        margin = 8

        f = painter.font()
        f.setPointSize(max(7, int(icon * 0.90)))
        painter.setFont(f)
        fm = painter.fontMetrics()

        def text_baseline(y_pos: int) -> int:
            return y_pos + (icon + fm.ascent()) // 2

        def _row(y_pos: int, brush: QBrush, label: str) -> int:
            painter.setPen(Colors.BLACK.value)
            painter.setBrush(brush)
            painter.drawRect(margin, y_pos, icon, icon)

            painter.setPen(QPen(Colors.BLACK.value, 0))
            painter.setBrush(Qt.NoBrush)
            painter.drawText(margin + icon + gap_x, text_baseline(y_pos), label)
            return y_pos + icon + gap_y

        y = margin

        gray_w = icon
        gray_h = icon
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.DARK_GRAY.value)
        painter.drawRect(margin, y, gray_w, gray_h)

        stripe_h = gray_h // 2
        stripe_y = y + (gray_h - stripe_h) // 2
        painter.setBrush(Colors.BLACK.value)
        painter.drawRect(margin, stripe_y, gray_w, stripe_h)

        painter.setPen(QPen(Colors.BLACK.value, 0))
        painter.setBrush(Qt.NoBrush)
        painter.drawText(margin + gray_w + gap_x, text_baseline(y), "Coated blade")

        y += icon + gap_y

        painter.setPen(QPen(Colors.BLUE.value, 4))
        line_x = margin + icon // 2
        painter.drawLine(line_x, y, line_x, y + icon)

        painter.setPen(QPen(Colors.BLACK.value, 0))
        painter.setBrush(Qt.NoBrush)
        painter.drawText(margin + icon + gap_x, text_baseline(y), "Beam guide")

        y += gray_h + gap_y

        y = _row(y, QBrush(Colors.GREEN.value), "Rotating")
        _row(y, QBrush(Colors.GRAY.value), "Parked")

        painter.restore()

    def calculate_grid(self, count, aspect_ratio):
        best_diff = float("inf")
        best_rows = 1
        best_cols = count

        for cols in range(1, count + 1):
            rows = math.ceil(count / cols)
            grid_aspect = cols / rows

            diff = abs(grid_aspect - aspect_ratio)
            if diff < best_diff:
                best_diff = diff
                best_rows = rows
                best_cols = cols

        return best_rows, best_cols

    def calculate_positions(self, count):
        if count == 0:
            return [], 0

        widget_width = self.width()
        widget_height = self.height()
        if widget_height == 0 or widget_width == 0:
            return [], 0

        aspect_ratio = widget_width / widget_height

        if count > 1:
            rows, cols = self.calculate_grid(count, aspect_ratio)

            padding_width = widget_width / cols / 6
            padding_height = widget_height / rows / 6

            cell_width = (widget_width - (cols + 1) * padding_width) / cols
            cell_height = (widget_height - (rows + 1) * padding_height) / rows

            chopper_radius = min(cell_width, cell_height) / 2

        else:
            rows, cols = 1, 1
            padding_width = widget_width / 6
            padding_height = widget_height / 6
            cell_width = widget_width - 2 * padding_width
            cell_height = widget_height - 2 * padding_height
            chopper_radius = min(cell_width, cell_height) / 2

        positions = []
        for idx in range(count):
            row = idx // cols
            col = idx % cols

            x = (
                padding_width
                + col * (cell_width + padding_width)
                + (cell_width + padding_width) / 2
            )
            y = (
                padding_height
                + row * (cell_height + padding_height)
                + (cell_height + padding_height) / 2
            )

            positions.append(QPointF(x, y))

        return positions, chopper_radius

    def _normalize_openings(self, slit_edges: list[list[float]]) -> list[list[float]]:
        """Normalize openings (slits) to merged, unwrapped [start,end] with end>=start.
        Keeps segments possibly >360 so we can represent wrap cleanly."""
        if not slit_edges:
            return []
        segs = []
        for s, e in slit_edges:
            s %= 360.0
            e %= 360.0
            if e < s:
                e += 360.0  # unwrap across 0°
            segs.append([s, e])
        segs.sort(key=lambda p: p[0])

        # merge overlaps
        merged = []
        for s, e in segs:
            if not merged:
                merged.append([s, e])
            else:
                ls, le = merged[-1]
                if s <= le + 1e-9:
                    merged[-1][1] = max(le, e)
                else:
                    merged.append([s, e])

        # If last overlaps first when wrapped (+360), merge them
        if len(merged) > 1:
            fs, fe = merged[0]
            ls, le = merged[-1]
            if le >= fs + 360.0 - 1e-9:
                merged[-1][1] = max(le, fe + 360.0)
                merged.pop(0)

        return merged

    def _sector_polygon(
        self,
        center: QPointF,
        inner_r: float,
        outer_r: float,
        start_deg: float,
        end_deg: float,
        rotation_deg: float,
        num_points: int = 72,
    ) -> QPolygonF:
        """Ring-sector polygon for [start_deg,end_deg] (math CCW degrees)."""
        # unwrap so end >= start
        s = start_deg
        e = end_deg
        if e < s:
            e += 360.0
        if e - s < 1e-6:
            return QPolygonF()

        def to_qt(a_deg: float) -> float:
            # Geometry is expressed in engineering CW+ angles.
            return math.radians(-a_deg + rotation_deg)

        step = (e - s) / num_points
        pts = []

        # outer arc s->e
        for i in range(num_points + 1):
            a = s + i * step
            ar = to_qt(a)
            pts.append(
                QPointF(
                    center.x() + outer_r * math.cos(ar),
                    center.y() - outer_r * math.sin(ar),
                )
            )
        # inner arc e->s
        for i in range(num_points + 1):
            a = e - i * step
            ar = to_qt(a)
            pts.append(
                QPointF(
                    center.x() + inner_r * math.cos(ar),
                    center.y() - inner_r * math.sin(ar),
                )
            )

        return QPolygonF(pts)

    def _annulus_with_opening_holes(
        self,
        center: QPointF,
        inner_r: float,
        outer_r: float,
        slit_edges: list[list[float]],
        rotation_deg: float,
    ) -> QPainterPath:
        """Build one path: full annulus MINUS all openings, using Odd-Even fill."""
        # Start with full annulus as a 360° sector
        ring = self._sector_polygon(
            center, inner_r, outer_r, 0.0, 360.0, rotation_deg, num_points=180
        )
        path = QPainterPath()
        if not ring.isEmpty():
            path.addPolygon(ring)

        openings = self._normalize_openings(slit_edges)
        for s, e in openings:
            hole = self._sector_polygon(center, inner_r, outer_r, s, e, rotation_deg)
            if not hole.isEmpty():
                path.addPolygon(hole)

        path.setFillRule(Qt.FillRule.OddEvenFill)
        return path.simplified()

    def draw_chopper(
        self,
        painter,
        center,
        radius,
        slit_edges,
        slit_height,
        rotation_angle,
        selected=False,
        moving=False,
    ):
        reduced_radius = radius - slit_height
        blades_path = self._annulus_with_opening_holes(
            center, reduced_radius, radius, slit_edges, rotation_angle
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(blades_path, QBrush(Colors.DARK_GRAY.value))

        inner_coating = reduced_radius + radius * 0.05
        outer_coating = radius * 0.95
        coating_path = self._annulus_with_opening_holes(
            center, inner_coating, outer_coating, slit_edges, rotation_angle
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(coating_path, QBrush(Colors.BLACK.value))

        painter.setBrush(QBrush(Colors.GREEN.value if moving else Colors.GRAY.value))
        painter.setPen(
            QPen(Colors.BLUE.value, 2) if selected else QPen(Colors.BLACK.value, 1)
        )
        painter.drawEllipse(center, radius - slit_height, radius - slit_height)

    def update_chopper_data(self, chopper_data):
        self.chopper_data = chopper_data
        self.angles = {
            i: self._default_rotation_offset for i in range(len(self.chopper_data))
        }
        self.update()

    def clear(self):
        self.chopper_data = []
        self.angles = {}
        self._selected_chopper = None
        self.update()


def traverse_json(json_obj, condition_fn, action_fn, path=[]) -> None:
    """
    Recursively traverse the JSON object applying a condition function
    at each node. If the condition is met, applies an action function.

    :param json_obj: The JSON object or part of it being traversed.
    :param condition_fn: A function that takes a node and returns
    True if the condition is met.
    :param action_fn: A function that performs an action
     on nodes that meet the condition.
    :param path: The current path to the node, used for
    tracking the node's location within the JSON.
    """
    if condition_fn(json_obj):
        action_fn(json_obj, path)

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            traverse_json(value, condition_fn, action_fn, path + [key])
    elif isinstance(json_obj, list):
        for index, item in enumerate(json_obj):
            traverse_json(item, condition_fn, action_fn, path + [index])


def find_all_nxdisk_choppers(json_obj) -> list[dict]:
    found_choppers = []

    def condition_fn(node):
        return (
            isinstance(node, dict)
            and "attributes" in node
            and any(
                attr.get("name") == "NX_class"
                and attr.get("values") == "NXdisk_chopper"
                for attr in node["attributes"]
            )
        )

    def action_fn(node, path):
        found_choppers.append(node)

    traverse_json(json_obj, condition_fn, action_fn)
    return found_choppers


def get_edges_from_nxdisk_choppers(choppers) -> dict[str, list[list[float]]]:
    edges = {}

    for chopper in choppers:
        for child in chopper.get("children", []):
            if (
                isinstance(child, dict)
                and "module" in child
                and child["module"] == "dataset"
            ):
                name = child.get("config", {}).get("name")
                if name == "slit_edges":
                    values = child.get("config", {}).get("values")
                    chopper_name = chopper.get("name", "Unknown Chopper")
                    edge_pairs = [
                        [values[i], values[i + 1]] for i in range(0, len(values), 2)
                    ]
                    edges[chopper_name] = edge_pairs

    return edges


def format_slit_edges(edge_data):
    return [{"slit_edges": data, "chopper": name} for name, data in edge_data.items()]


if __name__ == "__main__":
    json_path = "/home/jonas/code/nexus-json-templates/bifrost/bifrost-dynamic.json"
    with open(json_path, "r") as file:
        data = json.load(file)

    choppers = find_all_nxdisk_choppers(data)
    edges = get_edges_from_nxdisk_choppers(choppers)
    formatted_edges = format_slit_edges(edges)

    print(formatted_edges)

    app = QApplication(sys.argv)

    window = ChopperWidget()
    window.update_chopper_data(formatted_edges)
    window.show()

    sys.exit(app.exec_())

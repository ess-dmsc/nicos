import math
from enum import Enum
from typing import Optional

from nicos.guisupport.qt import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPointF,
    QPolygonF,
    QRectF,
    QSize,
    Qt,
    QWidget,
    pyqtSignal,
)
from nicos_ess.devices.epics.chopper import (
    CHOPPER_GUI_CHOPPER,
    CHOPPER_GUI_GUIDE_POSITION,
    CHOPPER_GUI_MOTOR_POSITION,
    CHOPPER_GUI_SLIT_EDGES,
    CHOPPER_RENDERED_GUIDE_ANGLE,
    CHOPPER_RENDERED_PARKING_ANGLE,
    CHOPPER_RENDERED_SPEED,
    is_chopper_moving,
)
from nicos_ess.gui.widgets.chopper_math import (
    build_rotation_model,
    has_canonical_inputs,
    parked_rotation_deg,
    runtime_spin_sign,
    spinning_rotation_deg,
    wrap360,
)


class Colors(Enum):
    GREEN = QColor(30, 255, 30, 255)
    GRAY = Qt.GlobalColor.gray
    BLUE = Qt.GlobalColor.blue
    DARK_GRAY = Qt.GlobalColor.darkGray
    BLACK = Qt.GlobalColor.black


class ChopperLegendWidget(QWidget):
    _PADDING_X = 9
    _PADDING_Y = 5
    _GAP_X = 7
    _ITEM_GAP = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(self.sizeHint())

    def sizeHint(self):
        fm = self.fontMetrics()
        icon = self._icon_size(fm)
        labels = ("Coated blade", "Beam guide", "Rotating", "Parked")
        width = self._PADDING_X * 2
        for index, label in enumerate(labels):
            width += icon + self._GAP_X + fm.horizontalAdvance(label)
            if index < len(labels) - 1:
                width += self._ITEM_GAP
        return QSize(width, icon + 2 * self._PADDING_Y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())

        fm = painter.fontMetrics()
        icon = self._icon_size(fm)
        x = self._PADDING_X
        y = max(self._PADDING_Y, (self.height() - icon) // 2)

        painter.setPen(QPen(QColor(0, 0, 0, 120), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            4,
            4,
        )

        def baseline() -> int:
            return y + (icon + fm.ascent()) // 2

        def text(label: str) -> None:
            nonlocal x
            painter.setPen(QPen(Colors.BLACK.value, 0))
            painter.setBrush(Qt.NoBrush)
            painter.drawText(x, baseline(), label)
            x += fm.horizontalAdvance(label) + self._ITEM_GAP

        gray_w = icon
        gray_h = icon
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.DARK_GRAY.value)
        painter.drawRect(x, y, gray_w, gray_h)
        stripe_h = gray_h // 2
        stripe_y = y + (gray_h - stripe_h) // 2
        painter.setBrush(Colors.BLACK.value)
        painter.drawRect(x, stripe_y, gray_w, stripe_h)
        x += gray_w + self._GAP_X
        text("Coated blade")

        painter.setPen(QPen(Colors.BLUE.value, max(2, icon // 4)))
        line_x = x + icon // 2
        painter.drawLine(line_x, y, line_x, y + icon)
        x += icon + self._GAP_X
        text("Beam guide")

        self._draw_color_item(painter, x, y, icon, Colors.GREEN.value, "Rotating")
        x += icon + self._GAP_X + fm.horizontalAdvance("Rotating") + self._ITEM_GAP
        self._draw_color_item(painter, x, y, icon, QBrush(Colors.GRAY.value), "Parked")

    def _icon_size(self, fm) -> int:
        return max(9, fm.height())

    def _draw_color_item(self, painter, x, y, icon, brush, label: str) -> None:
        painter.setPen(Colors.BLACK.value)
        painter.setBrush(brush)
        painter.drawRect(x, y, icon, icon)
        painter.setPen(QPen(Colors.BLACK.value, 0))
        painter.setBrush(Qt.NoBrush)
        fm = painter.fontMetrics()
        baseline = y + (icon + fm.ascent()) // 2
        painter.drawText(x + icon + self._GAP_X, baseline, label)


class ChopperWidget(QWidget):
    onChopperSelected = pyqtSignal(object)

    GUIDE_DIRS = {"RIGHT": 0.0, "UP": 90.0, "LEFT": 180.0, "DOWN": 270.0}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self.chopper_data = []
        self.angles = {}
        self._selected_chopper = None
        self._detailed_view = False
        self._show_guide_line = True

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
                self._selected_chopper = self.chopper_data[i][CHOPPER_GUI_CHOPPER]
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

    def set_detailed_view(self, enabled: bool) -> None:
        self._detailed_view = bool(enabled)
        self.update()

    def set_chopper_angle(self, chopper_name, angle):
        # Store raw device angle; mode-specific direction/offset handling happens
        # in paint-time bookkeeping based on speed and canonical metadata.
        for i, chopper in enumerate(self.chopper_data):
            if chopper[CHOPPER_GUI_CHOPPER] == chopper_name:
                if angle is None:
                    self.angles.pop(i, None)
                else:
                    self.angles[i] = wrap360(float(angle))
        self.update()

    def clear_chopper_angle(self, chopper_name) -> None:
        self.set_chopper_angle(chopper_name, None)

    def set_chopper_speed(self, chopper_name, speed):
        for chopper in self.chopper_data:
            if chopper[CHOPPER_GUI_CHOPPER] == chopper_name:
                chopper[CHOPPER_RENDERED_SPEED] = speed
                self.update()
                return

    def set_chopper_park_angle(self, chopper_name, angle):
        for chopper in self.chopper_data:
            if chopper[CHOPPER_GUI_CHOPPER] == chopper_name:
                chopper[CHOPPER_RENDERED_PARKING_ANGLE] = angle
                self.update()
                return

    def _canonical_rotation_base(
        self, chopper: dict, raw_angle: float, speed_hz: Optional[float], moving: bool
    ) -> float:
        if not has_canonical_inputs(chopper):
            raise ValueError(
                f"Chopper {chopper.get(CHOPPER_GUI_CHOPPER)!r} missing "
                "canonical bookkeeping inputs"
            )
        model = build_rotation_model(chopper)
        if moving:
            return spinning_rotation_deg(
                raw_angle,
                speed_hz,
                model.parked_opening_center_deg,
                model.tdc_resolver_position_deg,
                model.park_open_angle_deg,
                model.motor_position,
                model.positive_speed_rotation_direction,
                model.resolver_positive_direction,
                model.disk_delay_deg,
                model.cw_disk_delay_deg,
                model.ccw_disk_delay_deg,
            )
        return parked_rotation_deg(
            raw_angle,
            model.resolver_offset_deg,
            model.resolver_sign,
        )

    def get_rotation_angle_for_chopper(
        self, chopper_name: str, include_guide: bool = False
    ) -> Optional[float]:
        """Return current computed draw rotation for one chopper.

        This keeps tests focused on the widget's own bookkeeping without
        requiring panel/client setup.
        """
        for i, chopper in enumerate(self.chopper_data):
            if chopper[CHOPPER_GUI_CHOPPER] != chopper_name:
                continue
            speed_hz = chopper.get(CHOPPER_RENDERED_SPEED, 0.0)
            moving = is_chopper_moving(speed_hz)
            raw_angle = self.angles.get(i)
            if raw_angle is None:
                return None
            try:
                base_rotation = self._canonical_rotation_base(
                    chopper, float(raw_angle), speed_hz, moving
                )
            except ValueError:
                return None
            if include_guide:
                # Geometry conversion from engineering CW+ to Qt math-CCW.
                return wrap360(base_rotation + chopper[CHOPPER_RENDERED_GUIDE_ANGLE])
            return wrap360(base_rotation)
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
        return runtime_spin_sign(speed_hz, model.positive_speed_rotation_direction)

    def _spin_indicator_arc_angles(
        self, chopper: dict, spin_sign: int, span_deg: float = 72.0
    ) -> tuple[float, float]:
        guide_angle_deg = chopper[CHOPPER_RENDERED_GUIDE_ANGLE]
        half_span = span_deg / 2.0
        if spin_sign >= 0:
            start = guide_angle_deg + half_span
            end = guide_angle_deg - half_span
        else:
            start = guide_angle_deg - half_span
            end = guide_angle_deg + half_span
        return wrap360(start), wrap360(end)

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
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        chopper: dict,
        spin_sign: int,
    ) -> None:
        start_deg, end_deg = self._spin_indicator_arc_angles(chopper, spin_sign)
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
            slit_edges = chopper[CHOPPER_GUI_SLIT_EDGES]
            current_speed = chopper.get(CHOPPER_RENDERED_SPEED, 0.0)
            parking_angle = chopper.get(CHOPPER_RENDERED_PARKING_ANGLE, None)
            center = positions[i]
            guide_angle_deg = chopper[CHOPPER_RENDERED_GUIDE_ANGLE]

            is_selected = self._selected_chopper == chopper[CHOPPER_GUI_CHOPPER]
            is_moving = is_chopper_moving(current_speed)
            raw_angle = self.angles.get(i)
            if raw_angle is None:
                self._draw_unknown_chopper(painter, center, radius, is_selected)
                self._draw_chopper_labels(
                    painter,
                    center,
                    radius,
                    chopper,
                    is_selected,
                    None,
                    "Waiting",
                )
                continue
            try:
                base_rotation = self._canonical_rotation_base(
                    chopper, float(raw_angle), current_speed, is_moving
                )
            except ValueError:
                continue
            # Convert canonical engineering CW+ rotation to Qt math-CCW.
            angle = wrap360(base_rotation + guide_angle_deg)

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
                self._draw_chopper_details(
                    painter,
                    center,
                    radius,
                    chopper,
                    float(raw_angle),
                    current_speed,
                    is_moving,
                )

            if self._show_guide_line:
                painter.setPen(QPen(Colors.BLUE.value, 4))
                theta = math.radians(
                    guide_angle_deg
                )  # 0=right, 90=up, 180=left, 270=down
                line_x = center.x() + line_length * math.cos(theta)
                line_y = center.y() - line_length * math.sin(theta)
                painter.drawLine(center, QPointF(line_x, line_y))
            if is_moving:
                spin_sign = self._spin_direction_sign(chopper, current_speed)
                if spin_sign is not None:
                    self._draw_spin_direction_indicator(
                        painter, center, line_length * 0.5, chopper, spin_sign
                    )

            if current_speed is None:
                self._draw_chopper_labels(
                    painter,
                    center,
                    radius,
                    chopper,
                    is_selected,
                    None,
                    None,
                )
                continue

            if not is_moving and parking_angle is not None:
                value_text = f"{parking_angle:.3f}°"
            else:
                value_text = f"{current_speed:.3f} Hz"
            status_text = "Rotating" if is_moving else "Parked"
            self._draw_chopper_labels(
                painter,
                center,
                radius,
                chopper,
                is_selected,
                value_text,
                status_text,
            )

    def _draw_unknown_chopper(
        self, painter: QPainter, center: QPointF, radius: float, selected: bool
    ) -> None:
        painter.save()
        painter.setBrush(QBrush(QColor(190, 190, 190, 130)))
        painter.setPen(
            QPen(Colors.BLUE.value, 2) if selected else QPen(Colors.BLACK.value, 1)
        )
        painter.drawEllipse(center, radius * 0.7, radius * 0.7)
        painter.restore()

    def _draw_chopper_labels(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        chopper: dict,
        is_selected: bool,
        value_text: Optional[str],
        status_text: Optional[str],
    ) -> None:
        painter.setPen(Colors.BLUE.value if is_selected else Colors.BLACK.value)
        font = painter.font()
        font.setPointSize(int(radius / 8))
        painter.setFont(font)

        fm = painter.fontMetrics()
        text_height = fm.height()
        rows = [chopper[CHOPPER_GUI_CHOPPER]]
        if value_text is not None:
            rows.append(value_text)
        if status_text is not None:
            rows.append(status_text)
        rects = self._label_rects(chopper, center, radius, len(rows), text_height)

        for row, (rect, text) in enumerate(zip(rects, rows)):
            painter.setPen(
                Colors.BLUE.value if is_selected and row == 0 else Colors.BLACK.value
            )
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _label_rects(
        self,
        chopper: dict,
        center: QPointF,
        radius: float,
        row_count: int,
        row_height: float,
    ) -> list[QRectF]:
        text_direction = -1 if chopper[CHOPPER_RENDERED_GUIDE_ANGLE] == 270 else 1
        rects = [
            QRectF(
                center.x() - radius * 1.5,
                center.y() + (radius + 5) * text_direction,
                radius * 3.0,
                row_height * text_direction,
            )
        ]
        rects.extend(
            QRectF(
                center.x() - radius * 1.5,
                center.y() + row * row_height * text_direction,
                radius * 3.0,
                row_height * text_direction,
            )
            for row in range(1, row_count)
        )
        return rects

    def _draw_chopper_details(
        self,
        painter: QPainter,
        center: QPointF,
        radius: float,
        chopper: dict,
        raw_angle: float,
        speed_hz: Optional[float],
        is_moving: bool,
    ) -> None:
        motor_position = (
            str(chopper.get(CHOPPER_GUI_MOTOR_POSITION, "")).strip().lower()
        )
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

        reference = self._reference_marker_for_chopper(
            chopper, raw_angle, speed_hz, is_moving
        )
        if reference is not None:
            marker_angle, label = reference
            theta = math.radians(marker_angle)
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
            font = painter.font()
            font.setPointSize(max(7, int(radius * 0.11)))
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(label) + 8
            text_h = fm.height() + 2
            anchor = QPointF(
                center.x() + (radius * 1.10) * math.cos(theta),
                center.y() - (radius * 1.10) * math.sin(theta),
            )
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            if cos_t < -0.2:
                text_x = anchor.x() - text_w - 3
            elif cos_t > 0.2:
                text_x = anchor.x() + 3
            else:
                text_x = anchor.x() - text_w / 2
            if sin_t > 0.2:
                text_y = anchor.y() - text_h - 3
            elif sin_t < -0.2:
                text_y = anchor.y() + 3
            else:
                text_y = anchor.y() - text_h / 2
            painter.drawText(
                QRectF(text_x, text_y, text_w, text_h),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )
        painter.restore()

    def _reference_marker_for_chopper(
        self,
        chopper: dict,
        raw_angle: float,
        speed_hz: Optional[float],
        is_moving: bool,
    ) -> Optional[tuple[float, str]]:
        if not has_canonical_inputs(chopper):
            return None
        try:
            model = build_rotation_model(chopper)
        except ValueError:
            return None

        if is_moving:
            current_rotation = spinning_rotation_deg(
                raw_angle,
                speed_hz,
                model.parked_opening_center_deg,
                model.tdc_resolver_position_deg,
                model.park_open_angle_deg,
                model.motor_position,
                model.positive_speed_rotation_direction,
                model.resolver_positive_direction,
                model.disk_delay_deg,
                model.cw_disk_delay_deg,
                model.ccw_disk_delay_deg,
            )
            reference_rotation = spinning_rotation_deg(
                0.0,
                speed_hz,
                model.parked_opening_center_deg,
                model.tdc_resolver_position_deg,
                model.park_open_angle_deg,
                model.motor_position,
                model.positive_speed_rotation_direction,
                model.resolver_positive_direction,
                model.disk_delay_deg,
                model.cw_disk_delay_deg,
                model.ccw_disk_delay_deg,
            )
            label = "TDC"
        else:
            current_rotation = parked_rotation_deg(
                raw_angle,
                model.resolver_offset_deg,
                model.resolver_sign,
            )
            reference_rotation = parked_rotation_deg(
                model.tdc_resolver_position_deg,
                model.resolver_offset_deg,
                model.resolver_sign,
            )
            label = "TDC"

        marker_angle = wrap360(
            chopper[CHOPPER_RENDERED_GUIDE_ANGLE]
            + current_rotation
            - reference_rotation
        )
        return marker_angle, label

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
            raw_s = float(s)
            raw_e = float(e)
            raw_width = raw_e - raw_s
            s = raw_s % 360.0
            e = raw_e % 360.0
            if e == s and raw_width != 0.0:
                e = s + 360.0
            elif e < s:
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
        for chopper in chopper_data:
            build_rotation_model(chopper)
            chopper[CHOPPER_RENDERED_GUIDE_ANGLE] = self._to_guide_deg(
                chopper[CHOPPER_GUI_GUIDE_POSITION]
            )
        self.chopper_data = chopper_data
        self.angles = {}
        self.update()

    def clear(self):
        self.chopper_data = []
        self.angles = {}
        self._selected_chopper = None
        self.update()

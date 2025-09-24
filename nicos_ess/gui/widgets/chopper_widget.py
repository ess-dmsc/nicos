import json
import math
import sys
from enum import Enum

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


class Colors(Enum):
    GREEN = QColor(30, 255, 30, 255)
    GRAY = Qt.GlobalColor.gray
    BLUE = Qt.GlobalColor.blue
    DARK_GRAY = Qt.GlobalColor.darkGray
    BLACK = Qt.GlobalColor.black


class ChopperWidget(QWidget):
    onChopperSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self.chopper_data = []
        self.angles = {}
        self._selected_chopper = None
        self._default_rotation_offset = 90

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

    def set_chopper_angle(self, chopper_name, angle):
        for i, chopper in enumerate(self.chopper_data):
            if chopper["chopper"] == chopper_name:
                self.angles[i] = angle + self._default_rotation_offset
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
            resolver_offset = chopper.get("resolver_offset", 0.0)
            tdc_offset = chopper.get("tdc_offset", 0.0)
            current_speed = chopper.get("speed", 0.0)
            parking_angle = chopper.get("parking_angle", None)
            center = positions[i]

            is_selected = self._selected_chopper == chopper["chopper"]
            is_moving = (
                current_speed is not None and abs(current_speed) > 2
            )  # resolver is active under 2hz

            angle = self.angles[i]
            angle += tdc_offset if is_moving else resolver_offset

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

            painter.setPen(QPen(Colors.BLUE.value, 4))
            line_x = center.x()
            line_y = center.y() - line_length
            painter.drawLine(center, QPointF(line_x, line_y))

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
                center.y() + radius + 5,
                radius * 3.0,
                text_height,
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
                center.y() + text_height,
                radius * 3.0,
                text_height,
            )
            painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, value_text)

            status_text = "Rotating" if is_moving else "Parked"
            status_rect = QRectF(
                center.x() - radius * 1.5,
                center.y() + 2 * text_height,
                radius * 3.0,
                text_height,
            )
            painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, status_text)

        self.draw_legend(painter, chopper_radius)

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

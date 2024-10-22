from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QFrame,
    QComboBox,
    QGraphicsItem,
    QStyleOptionGraphicsItem,
    QGraphicsTextItem,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QCursor,
    QFont,
    QFontMetrics,
    QPainterPath,
    QPolygonF,
    Qt,
    QRectF,
    QPointF,
    QLineF,
)


class ShapeType:
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    PENTAGON = "pentagon"
    TRIANGLE = "triangle"


class ResizeHandle(QGraphicsRectItem):
    """Handle for resizing shapes."""

    def __init__(self, parent=None):
        super().__init__(-5, -5, 10, 10, parent)
        self.setBrush(QBrush(QColor("black")))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(11)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            parent = self.parentItem()
            if parent:
                if self.scene() and self.scene().views():
                    view = self.scene().views()[0]
                    grid_size = view.grid_size

                    rect = parent.rect()
                    new_width = value.x() - rect.x()
                    new_height = value.y() - rect.y()

                    new_width = round(new_width / grid_size) * grid_size
                    new_height = round(new_height / grid_size) * grid_size

                    new_width = max(new_width, 10)
                    new_height = max(new_height, 10)

                    parent.prepareGeometryChange()
                    rect.setWidth(new_width)
                    rect.setHeight(new_height)
                    parent.setRect(rect)

                    return QPointF(rect.right(), rect.bottom())
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        parent = self.parentItem()
        if parent:
            parent.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        parent = self.parentItem()
        if parent:
            parent.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        super().mouseReleaseEvent(event)


class ResizableShape(QGraphicsRectItem):
    """A shape that can be resized by dragging a handle."""

    def __init__(self, shape_type=ShapeType.RECTANGLE, parent=None):
        super().__init__(-25, -25, 50, 50, parent)
        self.shape_type = shape_type
        self.device = None
        self.device_value = 0
        self.device_status = None
        self.is_edit_mode = False

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(0)

        self.setBrush(QBrush(QColor("lightgray")))
        self.setPen(QPen(QColor("black"), 1))
        self.handle = None

        self.device_name_text = QGraphicsTextItem(self)
        self.device_value_text = QGraphicsTextItem(self)
        self.device_name_text.setPlainText("")
        self.device_value_text.setPlainText("")

        font = QFont()
        font.setPointSize(8)
        self.device_name_text.setFont(font)
        self.device_value_text.setFont(font)
        self.device_name_text.setDefaultTextColor(QColor("black"))
        self.device_value_text.setDefaultTextColor(QColor("black"))

        self.update_text_position()

    def set_device(self, device_name):
        self.device = device_name
        self.device_name_text.setPlainText(device_name or "")
        self.update_text_position()

    def update_value(self, value):
        self.device_value = value
        self.device_value_text.setPlainText(f"{value:.2f}")
        self.update_text_position()

    def update_status(self, status_tuple):
        code, status = status_tuple
        self.device_status = status
        if code == 200:
            self.setBrush(QBrush(QColor("green")))
        elif code < 300:
            self.setBrush(QBrush(QColor("yellow")))
        elif code < 500:
            self.setBrush(QBrush(QColor("orange")))
        else:
            self.setBrush(QBrush(QColor("red")))

    def update_text_position(self):
        rect = self.rect()

        max_font_size = int(rect.height() / 4)
        max_font_size = max(6, min(max_font_size, 20))

        font = QFont()
        font.setPointSize(max_font_size)

        for text_item in [self.device_name_text, self.device_value_text]:
            text_item.setFont(font)
            fm = QFontMetrics(font)
            text_width = fm.horizontalAdvance(text_item.toPlainText())
            while text_width > rect.width() - 4 and font.pointSize() > 6:
                font.setPointSize(font.pointSize() - 1)
                text_item.setFont(font)
                fm = QFontMetrics(font)
                text_width = fm.horizontalAdvance(text_item.toPlainText())

        name_fm = QFontMetrics(self.device_name_text.font())
        value_fm = QFontMetrics(self.device_value_text.font())

        total_text_height = name_fm.height() + value_fm.height()
        available_height = rect.height() - 4

        while total_text_height > available_height and font.pointSize() > 6:
            font.setPointSize(font.pointSize() - 1)
            for text_item in [self.device_name_text, self.device_value_text]:
                text_item.setFont(font)
            name_fm = QFontMetrics(self.device_name_text.font())
            value_fm = QFontMetrics(self.device_value_text.font())
            total_text_height = name_fm.height() + value_fm.height()

        name_text_width = name_fm.horizontalAdvance(self.device_name_text.toPlainText())
        value_text_width = value_fm.horizontalAdvance(
            self.device_value_text.toPlainText()
        )

        device_name_x = rect.x() + (rect.width() - name_text_width) / 2
        device_value_x = rect.x() + (rect.width() - value_text_width) / 2

        device_name_y = rect.y() + (rect.height() - total_text_height) / 2
        self.device_name_text.setPos(device_name_x, device_name_y)

        device_value_y = device_name_y + name_fm.height()
        self.device_value_text.setPos(device_value_x, device_value_y)

    def hoverEnterEvent(self, event):
        if self.is_edit_mode:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverEnterEvent(event)

    def mousePressEvent(self, event):
        if self.handle and self.handle.contains(
            self.mapToItem(self.handle, event.pos())
        ):
            event.ignore()
        else:
            if self.is_edit_mode:
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_edit_mode:
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)

    def _get_pentagon_points(self):
        rect = self.rect()
        width = rect.width()
        height = rect.height()

        points = []

        top_vertex = QPointF(rect.x() + width / 2, rect.y())

        left_vertex = QPointF(rect.x(), rect.y() + height * 0.4)
        right_vertex = QPointF(rect.x() + width, rect.y() + height * 0.4)

        bottom_left_vertex = QPointF(rect.x() + width * 0.25, rect.y() + height)
        bottom_right_vertex = QPointF(rect.x() + width * 0.75, rect.y() + height)

        points.append(top_vertex)
        points.append(left_vertex)
        points.append(bottom_left_vertex)
        points.append(bottom_right_vertex)
        points.append(right_vertex)

        return points

    def _get_triangle_points(self):
        rect = self.rect()
        width = rect.width()
        height = rect.height()

        points = []

        top_vertex = QPointF(rect.x() + width / 2, rect.y())
        bottom_left_vertex = QPointF(rect.x(), rect.y() + height)
        bottom_right_vertex = QPointF(rect.x() + width, rect.y() + height)

        points.append(top_vertex)
        points.append(bottom_left_vertex)
        points.append(bottom_right_vertex)

        return points

    def _get_shape_points(self):
        if self.shape_type == ShapeType.CIRCLE:
            return None
        elif self.shape_type == ShapeType.RECTANGLE:
            rect = self.rect()
            return [
                rect.topLeft(),
                rect.topRight(),
                rect.bottomRight(),
                rect.bottomLeft(),
            ]
        elif self.shape_type == ShapeType.TRIANGLE:
            return self._get_triangle_points()
        elif self.shape_type == ShapeType.PENTAGON:
            return self._get_pentagon_points()
        else:
            raise NotImplementedError(f"Shape {self.shape_type} not implemented")

    def _add_circle_path(self, path):
        path.addEllipse(self.rect())

    def _paint_circle(self, painter):
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(self.rect())

    def _paint_circle_outline(self, painter):
        painter.drawEllipse(self.rect())

    def _add_polygon_path(self, path):
        points = self._get_shape_points()
        if points:
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            path.closeSubpath()

    def _paint_polygon(self, painter):
        points = self._get_shape_points()
        if points:
            polygon = QPolygonF(points)
            painter.setBrush(self.brush())
            painter.setPen(self.pen())
            painter.drawPolygon(polygon)

    def _paint_polygon_outline(self, painter):
        points = self._get_shape_points()
        if points:
            polygon = QPolygonF(points)
            painter.drawPolygon(polygon)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget):
        if self.shape_type == ShapeType.CIRCLE:
            self._paint_circle(painter)
        else:
            self._paint_polygon(painter)

        if self.isSelected() and self.is_edit_mode:
            pen = QPen(Qt.GlobalColor.blue, 3, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.shape_type == ShapeType.CIRCLE:
                self._paint_circle_outline(painter)
            else:
                self._paint_polygon_outline(painter)

    def shape(self):
        path = QPainterPath()
        if self.shape_type == ShapeType.CIRCLE:
            self._add_circle_path(path)
        else:
            self._add_polygon_path(path)
        if self.handle:
            handle_path = self.handle.mapToParent(self.handle.shape())
            path = path.subtracted(handle_path)
        return path

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                if view.is_edit_mode:
                    grid_size = view.grid_size
                    x = round(value.x() / grid_size) * grid_size
                    y = round(value.y() / grid_size) * grid_size
                    return QPointF(x, y)
                else:
                    return self.pos()
        elif change in (
            QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemTransformChange,
            QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemScaleHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemRotationHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemEnabledHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemPositionChange,
        ):
            self.update_text_position()
        return super().itemChange(change, value)

    def set_edit_mode(self, edit_mode):
        self.is_edit_mode = edit_mode
        if edit_mode:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.add_resize_handle()
        else:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.remove_resize_handle()

    def add_resize_handle(self):
        if not self.handle:
            self.handle = ResizeHandle(self)
            rect = self.rect()
            self.handle.setPos(rect.right(), rect.bottom())
            self.handle.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            self.handle.setZValue(1)

    def remove_resize_handle(self):
        if self.handle:
            self.scene().removeItem(self.handle)
            self.handle = None

    def boundingRect(self):
        rect = super().boundingRect()

        device_name_polygon = self.device_name_text.mapToParent(
            self.device_name_text.boundingRect()
        )
        device_value_polygon = self.device_value_text.mapToParent(
            self.device_value_text.boundingRect()
        )

        device_name_rect = device_name_polygon.boundingRect()
        device_value_rect = device_value_polygon.boundingRect()

        total_rect = rect.united(device_name_rect).united(device_value_rect)

        if self.handle:
            handle_polygon = self.handle.mapToParent(self.handle.boundingRect())
            handle_rect = handle_polygon.boundingRect()
            total_rect = total_rect.united(handle_rect)

        return total_rect


class SynopticWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_edit_mode = False
        self.devices = []
        self.init_ui()

        self.scene.selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            shape = selected_items[0]
            if isinstance(shape, ResizableShape):
                self.show_settings_panel(shape)

    def init_ui(self):
        self.setWindowTitle("Synoptic Widget")
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)

        self.sidebar = QFrame()
        self.sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        self.sidebar_layout = QVBoxLayout()
        self.sidebar.setLayout(self.sidebar_layout)
        self.edit_mode_button = QPushButton("Edit Mode")
        self.edit_mode_button.setCheckable(True)
        self.edit_mode_button.clicked.connect(self.toggle_edit_mode)
        self.sidebar_layout.addWidget(self.edit_mode_button)
        self.add_rect_button = QPushButton("Add Rectangle")
        self.add_rect_button.clicked.connect(
            lambda: self.add_shape(ShapeType.RECTANGLE)
        )
        self.add_circle_button = QPushButton("Add Circle")
        self.add_circle_button.clicked.connect(lambda: self.add_shape(ShapeType.CIRCLE))
        # self.add_triangle_button = QPushButton('Add Triangle')
        # self.add_triangle_button.clicked.connect(
        #     lambda: self.add_shape(ShapeType.TRIANGLE)
        # )
        self.add_pentagon_button = QPushButton("Add Pentagon")
        self.add_pentagon_button.clicked.connect(
            lambda: self.add_shape(ShapeType.PENTAGON)
        )
        self.sidebar_layout.addWidget(self.add_rect_button)
        self.sidebar_layout.addWidget(self.add_circle_button)
        # self.sidebar_layout.addWidget(self.add_triangle_button)
        self.sidebar_layout.addWidget(self.add_pentagon_button)
        self.sidebar_layout.addStretch()
        self.layout.addWidget(self.sidebar)

        self.scene = QGraphicsScene(self)
        self.graphics_view = SynopticGraphicsView(self.scene)
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.layout.addWidget(self.graphics_view)

        self.settings_panel = QFrame()
        self.settings_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.settings_layout = QVBoxLayout()
        self.settings_panel.setLayout(self.settings_layout)
        self.device_label = QLabel("Device:")
        self.device_combo = QComboBox()
        self.device_combo.addItems([""] + self.devices)
        self.device_combo.currentTextChanged.connect(self.update_device_link)
        self.settings_layout.addWidget(self.device_label)
        self.settings_layout.addWidget(self.device_combo)
        self.settings_layout.addStretch()
        self.layout.addWidget(self.settings_panel)
        self.settings_panel.setVisible(False)

        self.shapes = []

    def set_device_list(self, devices):
        self.devices = devices
        self.device_combo.clear()
        self.device_combo.addItems([""] + devices)

    def toggle_edit_mode(self, checked):
        self.is_edit_mode = checked
        self.graphics_view.set_edit_mode(checked)
        self.add_rect_button.setEnabled(checked)
        self.add_circle_button.setEnabled(checked)
        self.add_pentagon_button.setEnabled(checked)
        for shape in self.shapes:
            shape.set_edit_mode(checked)
            shape.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, checked)
            if not checked:
                shape.setSelected(False)
        if not checked:
            self.settings_panel.setVisible(False)
        else:
            self.settings_panel.setVisible(True)

    def add_shape(self, shape_type):
        shape = ResizableShape(shape_type)

        grid_size = self.graphics_view.grid_size
        initial_size = grid_size * 4
        shape.setRect(-initial_size / 2, -initial_size / 2, initial_size, initial_size)

        shape.set_edit_mode(self.is_edit_mode)
        self.scene.addItem(shape)
        self.shapes.append(shape)

        self.deselect_all_shapes()

        shape.setPos(0, 0)
        shape.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        shape.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        shape.setSelected(True)
        self.show_settings_panel(shape)

    def update_device_link(self, device_name):
        selected_items = self.scene.selectedItems()
        if selected_items:
            shape = selected_items[0]
            shape.set_device(device_name or None)

    def on_client_cache(self, data):
        (time, key, op, value) = data
        device_name, attribute = key.split("/")
        for shape in self.shapes:
            if shape.device == device_name:
                if attribute == "value":
                    shape.update_value(value)
                elif attribute == "status":
                    shape.update_status(value)

    def resizeEvent(self, event):
        self.graphics_view.fitInView(
            self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio
        )
        super().resizeEvent(event)

    def show_settings_panel(self, shape):
        self.settings_panel.setVisible(True)
        self.device_combo.setCurrentText(shape.device or "")

    def deselect_all_shapes(self):
        for shape in self.shapes:
            shape.setSelected(False)


class SynopticGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.is_edit_mode = False
        self.grid_size = 20
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self.compute_scene_size()

    def set_edit_mode(self, edit_mode):
        self.is_edit_mode = edit_mode
        if edit_mode:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().update()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if self.is_edit_mode:
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)

            lines = []
            for x in range(left, int(rect.right()), self.grid_size):
                lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            for y in range(top, int(rect.bottom()), self.grid_size):
                lines.append(QLineF(rect.left(), y, rect.right(), y))

            painter.setPen(QPen(QColor(200, 200, 200, 50), 0))
            painter.drawLines(lines)

    def wheelEvent(self, event):
        zoom_factor = 1.15
        mouse_pos = event.position().toPoint()
        mouse_scene_pos = self.mapToScene(mouse_pos)

        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

        self.centerOn(mouse_scene_pos)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.RightButton:
            current_pos = self.mapToScene(event.pos())
            delta = current_pos - self._drag_start_pos
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if self.is_edit_mode and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, ResizableShape):
                self.parentWidget().show_settings_panel(item)
            elif isinstance(item, QGraphicsTextItem):
                shape = item.parentItem()
                self.parentWidget().show_settings_panel(shape)
            else:
                self.parentWidget().deselect_all_shapes()
                self.parentWidget().device_combo.setCurrentIndex(0)

        elif event.button() == Qt.MouseButton.RightButton:
            self._drag_start_pos = self.mapToScene(event.pos())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseReleaseEvent(event)

    def compute_scene_size(self, region=None):
        widget_rect_in_scene = QRectF(
            self.mapToScene(self.rect().topLeft()),
            self.mapToScene(self.rect().bottomRight()),
        )
        margin = 1000
        scale = self.transform().m11()
        margin /= scale
        expanded_rect = widget_rect_in_scene.adjusted(-margin, -margin, margin, margin)

        self.setSceneRect(expanded_rect)


class SynopticPanel(Panel):
    panelName = "Syntoptic"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self.synoptic_widget = SynopticWidget()

        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    def initialize_ui(self):
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

    def build_ui(self):
        self.main_layout.addWidget(self.synoptic_widget)

    def setup_connections(self, client):
        client.setup.connect(self.on_client_setup)
        client.connected.connect(self.on_client_connected)
        client.cache.connect(self.on_client_cache)

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

    def on_client_cache(self, data):
        (time, key, op, value) = data
        try:
            value = eval(value)
        except Exception:
            print(f"Failed to evaluate value: {value}")
            return
        self.synoptic_widget.on_client_cache((time, key, op, value))

    def _get_cached_value(self, key):
        result = self.client.ask("getcachekeys", key, default=[])
        return result

    def on_client_connected(self):
        self._update_device_list()

    def on_client_setup(self):
        self._update_device_list()

    def _update_device_list(self):
        state = self.client.ask("getstatus")
        if not state:
            return
        devlist = state["devices"]
        self.synoptic_widget.set_device_list(devlist)

    def closeEvent(self, event):
        return QMainWindow.closeEvent(self, event)

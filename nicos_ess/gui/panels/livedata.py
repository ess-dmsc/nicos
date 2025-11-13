"""NICOS LiveData liveview."""

from functools import partial

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QSplitter,
    Qt,
    QVBoxLayout,
    QWidget,
    pyqtSlot,
)
from nicos_ess.gui.widgets.pyqtgraph.image_view import ImageView
from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView, TimeAxisItem


class LayoutDialog(QDialog):
    """Simple dialog with two spin-boxes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot grid size")
        self.rows_sb = QSpinBox(minimum=1, maximum=6, value=2)
        self.cols_sb = QSpinBox(minimum=1, maximum=6, value=2)
        form = QFormLayout(self)
        form.addRow("Rows:", self.rows_sb)
        form.addRow("Columns:", self.cols_sb)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        form.addWidget(btn_box)

    @property
    def dims(self):
        return self.rows_sb.value(), self.cols_sb.value()


class LiveDataPlot(QFrame):
    """
    A self-contained widget for one plot, including a data-source combo box,
    a settings button, and a container for the live plot view.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.current_view = None
        self.build_ui()
        self.source_combo.currentIndexChanged.connect(self.on_plot_changed)

    def build_ui(self):
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.top_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItem("None")
        self.settings_btn = QPushButton("Settings")
        self.top_layout.addWidget(self.source_combo)
        self.top_layout.addWidget(self.settings_btn)
        self.main_layout.addLayout(self.top_layout)

        self.plot_container = QFrame()
        self.plot_container_layout = QVBoxLayout(self.plot_container)
        self.plot_container.setLayout(self.plot_container_layout)
        self.main_layout.addWidget(self.plot_container)

    @pyqtSlot()
    def on_plot_changed(self):
        selection = self.source_combo.currentText()

        if self.current_view is not None:
            self.plot_container_layout.removeWidget(self.current_view)
            self.current_view.deleteLater()
            self.current_view = None

        if selection == "None":
            parent = self.parent
            if parent:
                parent.connected_plots.pop(selection, None)
                parent.currently_selected_plots.pop(self, None)
            return

        parent = self.parent
        if selection not in parent.available_plots:
            return

        params, blobs = parent.available_plots[selection]
        datadesc = params["datadescs"][0]
        shape = datadesc["shape"]

        if len(shape) == 1:
            view = LineView(parent=self.parent)
            view.mode_checkbox.hide()
            view.clear_button.hide()
            view.log_checkbox.hide()
        elif len(shape) == 2:
            view = ImageView(parent=self.parent, histogram_orientation="vertical")
            view.aspectLockedAction.setChecked(False)
            view.set_aspect_locked(False)
            # invert Y compared to default
            view.image_plot.invertY()
            view.add_image_axes()
            view.splitter_vert_1.hide()
            view.bottom_plot.hide()
        else:
            return

        self.plot_container_layout.addWidget(view)
        view.show()
        self.current_view = view

        parent.connected_plots[selection] = (view, self.source_combo)
        parent.currently_selected_plots[self] = selection

        parent._on_plot_livedata(view, params, blobs)

    def update_combobox(self, choices, current_text):
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem("None")
        for choice in choices:
            self.source_combo.addItem(choice)
        new_index = self.source_combo.findText(current_text)
        if new_index != -1:
            self.source_combo.setCurrentIndex(new_index)
        self.source_combo.blockSignals(False)


class LiveDataPanel(Panel):
    panelName = "LiveData Panel"

    available_plots = {}
    connected_plots = {}
    currently_selected_plots = {}

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self.plot_widgets = []
        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    @pyqtSlot()
    def show_layout_dialog(self):
        dlg = LayoutDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            rows, cols = dlg.dims
            self.create_splitter_grid(rows, cols)

    def initialize_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def build_ui(self):
        self.layout_btn = QPushButton("Set plot configuration…")
        self.layout_btn.clicked.connect(self.show_layout_dialog)
        self.layout().addWidget(self.layout_btn)

        self.grid_root = None
        self.create_splitter_grid(2, 2)

    def create_splitter_grid(self, rows: int, cols: int):
        """
        Rebuild the plot matrix as an rows×cols web of QSplitters.
        Dragging a handle in one row / column mirrors the change in
        every sibling splitter so the grid acts like a single entity.
        """
        if self.grid_root is not None:
            self.layout().removeWidget(self.grid_root)
            self.grid_root.deleteLater()
        self.plot_widgets.clear()
        self.connected_plots.clear()
        self.currently_selected_plots.clear()

        root = QSplitter(Qt.Orientation.Vertical, self)
        row_splitters: list[QSplitter] = []
        col_splitters: list[QSplitter] = []

        for r in range(rows):
            hsplit = QSplitter(Qt.Orientation.Horizontal, root)
            row_splitters.append(hsplit)
            for c in range(cols):
                plot = LiveDataPlot(self)
                self.plot_widgets.append(plot)
                hsplit.addWidget(plot)

                if len(col_splitters) < cols:
                    vs = QSplitter(Qt.Orientation.Vertical)
                    col_splitters.append(hsplit)

        for sp in row_splitters:
            sp.splitterMoved.connect(partial(self._mirror_sizes, sp, row_splitters))

        self.layout().addWidget(root)
        self.grid_root = root
        root.show()

    @staticmethod
    def _mirror_sizes(sender: QSplitter, siblings: list[QSplitter]):
        """Copy the sender’s size distribution onto every sibling."""
        sizes = sender.sizes()
        for sp in siblings:
            if sp is sender:
                continue
            sp.blockSignals(True)
            sp.setSizes(sizes)
            sp.blockSignals(False)

    def setup_connections(self, client):
        client.livedata.connect(self.on_client_livedata)
        client.connected.connect(self.on_client_connected)

    def _on_plot_livedata(self, plot_widget, params, blobs):
        name = params["det"]
        if name not in self.connected_plots:
            return

        datadesc = params["datadescs"][0]
        data_shape = datadesc["shape"]
        data_dtype = datadesc["dtype"]
        plot_type = datadesc.get("plot_type")

        # ---- decode data buffer ----
        data = np.frombuffer(blobs[0], dtype=data_dtype).reshape(tuple(data_shape))

        # ---- decode label buffer(s) ----
        label_shape = datadesc.get("label_shape", [])
        label_dtypes = datadesc.get("label_dtypes") or [np.dtype(np.float64).str] * len(
            label_shape
        )
        labels = []
        if label_shape:
            raw = blobs[1]  # single concatenated float64 buffer
            offset = 0
            for shape, dtype in zip(label_shape, label_dtypes):
                nbytes = shape * 8  # float64
                arr = np.frombuffer(
                    raw[offset : offset + nbytes], dtype=np.float64
                ).astype(dtype)
                labels.append(arr)
                offset += nbytes
        else:
            # robust fallback: synthetic indices
            if len(data_shape) >= 1:
                labels = [np.arange(data_shape[-1], dtype=np.float64)]
            if len(data_shape) >= 2:
                labels = [
                    np.arange(data_shape[1], dtype=np.float64),
                    np.arange(data_shape[0], dtype=np.float64),
                ]

        # ---- titles & axis labels (from datadesc metadata) ----
        axis_names = datadesc.get("axis_names", [])
        axis_units = datadesc.get("axis_units", [])
        title = datadesc.get("title") or params["det"]
        signal_unit = datadesc.get("signal_unit") or ""
        x_is_time = bool(datadesc.get("x_is_time", False))

        if plot_type == "hist-1d" and isinstance(plot_widget, LineView):
            # Apply axis/title formatting BEFORE plotting
            x_name = (
                axis_names[0] if len(axis_names) >= 1 else "Time" if x_is_time else "X"
            )
            y_name = "Counts"
            y_unit = signal_unit

            plot_widget.set_axis_format(
                title=title,
                x_label=x_name,
                y_label=y_name,
                y_units=y_unit,
                x_is_time=x_is_time,
            )

            plot_widget.set_data([data], {"x": labels[0]})

        elif plot_type == "hist-2d" and isinstance(plot_widget, ImageView):
            # data is 2D → labels[0]=x, labels[1]=y
            plot_widget.set_data(
                [data], {"x": labels[0], "y": labels[1]}, autoLevels=True
            )

            x_name = axis_names[0] if len(axis_names) >= 1 else "X"
            y_name = axis_names[1] if len(axis_names) >= 2 else "Y"
            x_unit = axis_units[0] if len(axis_units) >= 1 else ""
            y_unit = axis_units[1] if len(axis_units) >= 2 else ""

            plot_widget.image_plot.setTitle(title)
            plot_widget.image_plot.setLabel("bottom", x_name, units=x_unit)
            plot_widget.image_plot.setLabel("left", y_name, units=y_unit)
        else:
            return

    def _update_comboboxes(self):
        for plot_widget in self.plot_widgets:
            current_text = plot_widget.source_combo.currentText()
            plot_widget.update_combobox(self.available_plots.keys(), current_text)

    def on_client_livedata(self, params, blobs):
        self.log.debug("on_client_livedata: %r", params)

        self.available_plots[params["det"]] = (params, blobs)
        self._update_comboboxes()

        selected_plot, selected_cb = self.connected_plots.get(
            params["det"], (None, None)
        )
        if selected_plot and selected_cb:
            if selected_cb.currentText() == params["det"]:
                self._on_plot_livedata(selected_plot, params, blobs)

    def on_client_connected(self):
        self.client.tell("eventunmask", ["livedata"])

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

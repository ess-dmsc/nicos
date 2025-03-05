"""NICOS BeamLime liveview."""

import numpy as np
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from nicos.clients.gui.panels import Panel
from nicos_ess.gui.widgets.pyqtgraph.image_view import ImageView
from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView


class BeamLimePlot(QFrame):
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
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.top_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItem("None")
        self.settings_btn = QToolButton()
        self.settings_btn.setText("Settings")
        self.settings_menu = QMenu(self)
        self.settings_btn.setMenu(self.settings_menu)
        self.settings_btn.setPopupMode(QToolButton.InstantPopup)

        self.define_roi_action = QAction("Define ROI", self)
        self.define_roi_action.triggered.connect(self.on_define_roi_clicked)
        self.settings_menu.addAction(self.define_roi_action)

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
            view = ImageView(
                parent=self.parent, histogram_orientation="vertical", simple_mode=True
            )
            view.set_aspect_locked(False)
            view.add_image_axes()
            view.splitter_vert_1.hide()
            view.bottom_plot.hide()
            view.left_plot.hide()
        else:
            return

        self.plot_container_layout.addWidget(view)
        view.show()
        self.current_view = view

        parent.connected_plots[selection] = (view, self.source_combo)
        parent.currently_selected_plots[self] = selection

        parent._on_plot_livedata(view, params, blobs)

    def on_define_roi_clicked(self):
        """Slot triggered by the Define ROI menu action."""
        if not self.current_view:
            return  # No plot selected; do nothing

        # Only make sense if the current_view is an ImageView
        if isinstance(self.current_view, ImageView):
            # Show the ROI if it was hidden
            self.current_view.show_roi()  # shows the actual rectangular ROI
            self.current_view.hide_all_plots()
            # or if you want to start from an invisible ROI, do not show it yet

            # Switch into the “drag to define a new rectangle ROI” mode:
            self.current_view.enter_roi_drag_mode()

            # Optionally, register a callback so we get ROI data whenever ROI changes:
            self.current_view.register_roi_callback(self._roi_updated_callback)

        else:
            print("Not an image view; ROI definition is not applicable for 1D plots.")

    def _roi_updated_callback(self, data, coords):
        """
        Called whenever the user finishes dragging or changes the ROI in the ImageView.
        You receive the ROI sub-array (data) and the mapped coordinates (coords).
        """
        print("ROI updated callback in BeamLimePlot!")
        print(
            f"ROI shape = {data.shape}, ROI coords shape = {coords[0].shape}, {coords[1].shape}"
        )

        # DO WHATEVER YOU WANT HERE:
        # e.g., compute some stats, forward them to a logger, or store them in self.parent
        roi_mean = data.mean()
        roi_std = data.std()
        print(f"ROI mean={roi_mean:.3f}, std={roi_std:.3f}")

        # If you want to call the parent panel, do something like:
        if hasattr(self.parent, "on_roi_data"):
            self.parent.on_roi_data(self, data, coords)

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


class BeamLimePanel(Panel):
    panelName = "BeamLime Panel"

    available_plots = {}
    connected_plots = {}
    currently_selected_plots = {}

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        self.plot_widgets = []
        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

        self.start_simulator()

    def initialize_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def build_ui(self):
        self.add_plot_btn = QPushButton("Add Plot")
        self.add_plot_btn.clicked.connect(self.add_plot_widget)
        self.layout().addWidget(self.add_plot_btn)

        self.plots_container = QWidget()
        self.plots_layout = QGridLayout(self.plots_container)
        self.plots_container.setLayout(self.plots_layout)
        self.layout().addWidget(self.plots_container)

        for _ in range(2):
            self.add_plot_widget()

    def add_plot_widget(self):
        plot_widget = BeamLimePlot(self)
        self.plot_widgets.append(plot_widget)
        col_count = 2
        index = len(self.plot_widgets) - 1
        row = index // col_count
        col = index % col_count
        self.plots_layout.addWidget(plot_widget, row, col)
        for i in range(self.plots_layout.rowCount()):
            self.plots_layout.setRowStretch(i, 1)
        for i in range(self.plots_layout.columnCount()):
            self.plots_layout.setColumnStretch(i, 1)

    def setup_connections(self, client):
        client.livedata.connect(self.on_client_livedata)
        client.connected.connect(self.on_client_connected)

    def _on_plot_livedata(self, plot_widget, params, blobs):
        name = params["det"]

        if name not in self.connected_plots:
            return

        datadesc = params["datadescs"][0]
        data_shape = datadesc["shape"]
        label_shape = datadesc.get("label_shape", [])
        data_dtype = datadesc["dtype"]
        label_dtypes = datadesc.get("label_dtypes")
        plot_type = datadesc.get("plot_type")

        data = np.frombuffer(blobs[0], dtype=data_dtype).reshape(data_shape)
        labels = []
        for i, (shape, dtype) in enumerate(zip(label_shape, label_dtypes)):
            label = np.frombuffer(
                blobs[1][i * shape * 8 : (i + 1) * shape * 8], dtype=np.float64
            ).astype(dtype)
            labels.append(label)

        if plot_type == "hist-1d" and isinstance(plot_widget, LineView):
            plot_widget.set_data([data], {"x": labels[0]})
        elif plot_type == "hist-2d" and isinstance(plot_widget, ImageView):
            plot_widget.set_data([data], {"x": labels[1], "y": labels[0]})
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

    def on_roi_data(self, child_plot_widget, data, coords):
        print(
            f"ROI data received in BeamLimePanel from {child_plot_widget}: {data.shape}, {coords[0].shape}, {coords[1].shape}"
        )

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

    def start_simulator(self):
        """Starts a QTimer that periodically generates fake 2D data."""
        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self.push_simulated_data)
        self._sim_timer.start(1000)  # every 1 second

    def push_simulated_data(self):
        """Generate random 2D data and push it to the panel as if from livedata."""
        # Dimensions for the simulated 2D data
        nx, ny = 50, 50
        data = np.random.random((nx, ny))

        # Build fake edges for x and y (typical for a 2D histogram's bin edges)
        x_edges = np.linspace(0, nx, nx + 1)
        y_edges = np.linspace(0, ny, ny + 1)

        # Construct the params dict that 'on_client_livedata' expects
        params = {
            "det": "Sim2D",  # The source name
            "datadescs": [
                {
                    "shape": [nx, ny],
                    "dtype": data.dtype,  # e.g. float64
                    "plot_type": "hist-2d",
                    "label_shape": [nx + 1, ny + 1],  # The bin edges
                    "label_dtypes": [data.dtype, data.dtype],
                }
            ],
        }

        # Convert the data to bytes
        data_buf = data.tobytes()

        # Convert the x_edges and y_edges to bytes, in the order the code expects:
        #  - i=0 => x edges
        #  - i=1 => y edges
        #  We'll just concatenate them: x_edges then y_edges
        label_buf = x_edges.tobytes() + y_edges.tobytes()

        # This is the 'blobs' list: [image_data, label_data]
        blobs = [data_buf, label_buf]

        # Now we call the same method that would be called if real livedata arrived
        self.on_client_livedata(params, blobs)

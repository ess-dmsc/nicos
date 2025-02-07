"""NICOS BeamLime liveview."""

import numpy as np
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QPushButton,
    QComboBox,
)
from nicos.clients.gui.panels import Panel

from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView
from nicos_ess.gui.widgets.pyqtgraph.image_view import ImageView


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
            view.set_aspect_locked(False)
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
            plot_widget.set_data([data], {"x": labels[0], "y": labels[1]})
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


# """NICOS BeamLime liveview."""
#
# import numpy as np
# from PyQt5.QtWidgets import QFrame
#
# from nicos.clients.gui.panels import Panel
# from nicos.guisupport.qt import (
#     QSplitter,
#     Qt,
#     QVBoxLayout,
#     pyqtSlot,
#     QComboBox,
#     QHBoxLayout,
#     QPushButton,
# )
#
# from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView
# from nicos_ess.gui.widgets.pyqtgraph.image_view import ImageView
#
# TAB_WIDGET_MIN_WIDTH = 200
# DEFAULT_TAB_WIDGET_MIN_WIDTH = 0
# TAB_WIDGET_MAX_WIDTH = 200
# DEFAULT_TAB_WIDGET_MAX_WIDTH = 16777215
# VIEW_SPLITTER_SIZES = [600, 600, 100]
#
#
# class BeamLimePanel(Panel):
#     panelName = "BeamLime Panel"
#
#     available_plots = {}
#     connected_plots = {}
#     currently_selected_plots = {}
#
#     def __init__(self, parent, client, options):
#         Panel.__init__(self, parent, client, options)
#
#         self.initialize_ui()
#         self.build_ui()
#         self.setup_connections(client)
#
#     def initialize_ui(self):
#         layout = QVBoxLayout()
#         self.setLayout(layout)
#
#     def build_ui(self):
#         self.splitter_vert_1 = QSplitter(Qt.Orientation.Vertical)
#         self.splitter_vert_2 = QSplitter(Qt.Orientation.Vertical)
#         self.splitter_hori = QSplitter(Qt.Orientation.Horizontal)
#
#         self.upper_left_frame = QFrame()
#         self.upper_left_layout = QVBoxLayout()
#         self.upper_right_frame = QFrame()
#         self.upper_right_layout = QVBoxLayout()
#         self.lower_left_frame = QFrame()
#         self.lower_left_layout = QVBoxLayout()
#         self.lower_right_frame = QFrame()
#         self.lower_right_layout = QVBoxLayout()
#
#         for frame in [
#             self.upper_left_frame,
#             self.upper_right_frame,
#             self.lower_left_frame,
#             self.lower_right_frame,
#         ]:
#             frame.setFrameStyle(QFrame.Box)
#             frame.setLineWidth(1)
#
#         self.upper_left_cb = QComboBox()
#         self.upper_right_cb = QComboBox()
#         self.lower_left_cb = QComboBox()
#         self.lower_right_cb = QComboBox()
#
#         self.upper_left_setting_btn = QPushButton("Settings")
#         self.upper_right_setting_btn = QPushButton("Settings")
#         self.lower_left_setting_btn = QPushButton("Settings")
#         self.lower_right_setting_btn = QPushButton("Settings")
#
#         self.upper_left_hbox = QHBoxLayout()
#         self.upper_right_hbox = QHBoxLayout()
#         self.lower_left_hbox = QHBoxLayout()
#         self.lower_right_hbox = QHBoxLayout()
#
#         self.upper_left_hbox.addWidget(self.upper_left_cb)
#         self.upper_left_hbox.addWidget(self.upper_left_setting_btn)
#         self.upper_right_hbox.addWidget(self.upper_right_cb)
#         self.upper_right_hbox.addWidget(self.upper_right_setting_btn)
#         self.lower_left_hbox.addWidget(self.lower_left_cb)
#         self.lower_left_hbox.addWidget(self.lower_left_setting_btn)
#         self.lower_right_hbox.addWidget(self.lower_right_cb)
#         self.lower_right_hbox.addWidget(self.lower_right_setting_btn)
#
#         self.upper_left_layout.addLayout(self.upper_left_hbox)
#         self.upper_right_layout.addLayout(self.upper_right_hbox)
#         self.lower_left_layout.addLayout(self.lower_left_hbox)
#         self.lower_right_layout.addLayout(self.lower_right_hbox)
#
#         self.upper_left_frame.setLayout(self.upper_left_layout)
#         self.upper_right_frame.setLayout(self.upper_right_layout)
#         self.lower_left_frame.setLayout(self.lower_left_layout)
#         self.lower_right_frame.setLayout(self.lower_right_layout)
#
#         self.splitter_vert_1.addWidget(self.upper_left_frame)
#         self.splitter_vert_1.addWidget(self.upper_right_frame)
#         self.splitter_vert_2.addWidget(self.lower_left_frame)
#         self.splitter_vert_2.addWidget(self.lower_right_frame)
#
#         self.splitter_hori.addWidget(self.splitter_vert_1)
#         self.splitter_hori.addWidget(self.splitter_vert_2)
#         self.layout().addWidget(self.splitter_hori)
#
#     def setup_connections(self, client):
#         client.livedata.connect(self.on_client_livedata)
#         client.connected.connect(self.on_client_connected)
#
#         self.splitter_vert_1.splitterMoved.connect(
#             lambda x: self.splitter_moved(self.splitter_vert_1)
#         )
#         self.splitter_vert_2.splitterMoved.connect(
#             lambda x: self.splitter_moved(self.splitter_vert_2)
#         )
#
#         self.upper_left_cb.currentIndexChanged.connect(
#             lambda x: self._on_plot_changed(
#               self.upper_left_cb, self.upper_left_layout
#             )
#         )
#         self.upper_right_cb.currentIndexChanged.connect(
#             lambda x: self._on_plot_changed(
#                 self.upper_right_cb, self.upper_right_layout
#             )
#         )
#         self.lower_left_cb.currentIndexChanged.connect(
#             lambda x: self._on_plot_changed(
#               self.lower_left_cb, self.lower_left_layout
#             )
#         )
#         self.lower_right_cb.currentIndexChanged.connect(
#             lambda x: self._on_plot_changed(
#                 self.lower_right_cb, self.lower_right_layout
#             )
#         )
#
#     def _recursive_delete_layout(self, layout, ignore_list=[]):
#         for i in reversed(range(layout.count())):
#             item = layout.itemAt(i)
#             if item.layout():
#                 self._recursive_delete_layout(item.layout(), ignore_list)
#             else:
#                 if item.widget() in ignore_list:
#                     continue
#                 item.widget().deleteLater()
#
#     @pyqtSlot()
#     def _on_plot_changed(self, cb, layout):
#         index = cb.currentIndex()
#         current_plot_text = cb.currentText()
#         self._recursive_delete_layout(layout, ignore_list=[cb])
#
#         if index == 0:
#             name = self.currently_selected_plots.get(layout, None)
#             if name:
#                 self.connected_plots.pop(name, None)
#                 self.currently_selected_plots.pop(layout, None)
#             return
#
#         params, blobs = self.available_plots[current_plot_text]
#         datadesc = params["datadescs"][0]
#         shape = datadesc["shape"]
#         if len(shape) == 1:
#             view = LineView(parent=self)
#             view.mode_checkbox.hide()
#             view.clear_button.hide()
#             view.log_checkbox.hide()
#         elif len(shape) == 2:
#             view = ImageView(parent=self, histogram_orientation="vertical")
#             view.set_aspect_locked(False)
#             view.add_image_axes()
#             view.splitter_vert_1.hide()
#             view.bottom_plot.hide()
#         else:
#             return
#
#         self._update_comboboxes()
#         self.connected_plots[current_plot_text] = (view, cb)
#         self.currently_selected_plots[layout] = current_plot_text
#         layout.addWidget(view)
#         view.show()
#
#         self._on_plot_livedata(view, params, blobs)
#
#     @pyqtSlot()
#     def splitter_moved(self, sender):
#         receiver = (
#             self.splitter_vert_1
#             if sender is self.splitter_vert_2
#             else self.splitter_vert_2
#         )
#         receiver.blockSignals(True)
#         receiver.setSizes(sender.sizes())
#         receiver.blockSignals(False)
#
#     def exec_command(self, command):
#         self.client.tell("exec", command)
#
#     def eval_command(self, command, *args, **kwargs):
#         return self.client.eval(command, *args, **kwargs)
#
#     def _on_plot_livedata(self, plot_widget, params, blobs):
#         name = params["det"]
#
#         if name not in self.connected_plots:
#             return
#
#         data_shape = params["datadescs"][0]["shape"]
#         label_shape = params["datadescs"][0].get("label_shape", [])
#         data_dtype = params["datadescs"][0]["dtype"]
#         label_dtypes = params["datadescs"][0].get("label_dtypes")
#         plot_type = params["datadescs"][0].get("plot_type")
#
#         data = np.frombuffer(blobs[0], dtype=data_dtype).reshape(data_shape)
#         labels = []
#         for i, (shape, dtype) in enumerate(zip(label_shape, label_dtypes)):
#             label = np.frombuffer(
#                 blobs[1][i * shape * 8 : (i + 1) * shape * 8], dtype=np.float64
#             ).astype(dtype)
#             labels.append(label)
#
#         if plot_type == "hist-1d" and isinstance(plot_widget, LineView):
#             plot_widget.set_data([data], {"x": labels[0]})
#         elif plot_type == "hist-2d" and isinstance(plot_widget, ImageView):
#             plot_widget.set_data([data], {"x": labels[0], "y": labels[1]})
#         else:
#             return
#
#     def on_client_livedata(self, params, blobs):
#         self.log.debug("on_client_livedata: %r", params)
#
#         self.available_plots[params["det"]] = (params, blobs)
#         self._update_comboboxes()
#
#         selected_plot, selected_cb = self.connected_plots.get(
#             params["det"], (None, None)
#         )
#         if selected_plot and selected_cb:
#             if selected_cb.currentText() == params["det"]:
#                 self._on_plot_livedata(selected_plot, params, blobs)
#
#     def _update_comboboxes(self):
#         for cb in [
#             self.upper_left_cb,
#             self.upper_right_cb,
#             self.lower_left_cb,
#             self.lower_right_cb,
#         ]:
#             all_choices = [cb.itemText(i) for i in range(cb.count())]
#             if set(all_choices) == set(self.available_plots.keys()).union({"None"}):
#                 continue
#             current_text = cb.currentText()
#             cb.blockSignals(True)
#             cb.clear()
#             cb.addItem("None")
#             cb.addItems(self.available_plots.keys())
#             new_index = cb.findText(current_text)
#             if new_index:
#                 cb.setCurrentIndex(new_index)
#             cb.blockSignals(False)
#
#     def on_client_connected(self):
#         self.client.tell("eventunmask", ["livedata"])
#         # self.detectorskey = self._query_detectorskey()

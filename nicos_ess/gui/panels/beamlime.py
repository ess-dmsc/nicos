"""NICOS livewidget with pyqtgraph."""

import numpy as np
from PyQt5.QtWidgets import QFrame

from nicos.clients.gui.panels import Panel
from nicos.guisupport.qt import (
    QSplitter,
    Qt,
    QVBoxLayout,
    pyqtSlot,
    QComboBox,
)

from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView
from nicos_ess.gui.widgets.pyqtgraph.image_view import ImageView

TAB_WIDGET_MIN_WIDTH = 200
DEFAULT_TAB_WIDGET_MIN_WIDTH = 0
TAB_WIDGET_MAX_WIDTH = 200
DEFAULT_TAB_WIDGET_MAX_WIDTH = 16777215
VIEW_SPLITTER_SIZES = [600, 600, 100]


class BeamLimePanel(Panel):
    panelName = "BeamLime Panel"

    available_plots = {}
    connected_plots = {}

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    def initialize_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def build_ui(self):
        self.splitter_vert_1 = QSplitter(Qt.Orientation.Vertical)
        self.splitter_vert_2 = QSplitter(Qt.Orientation.Vertical)
        self.splitter_hori = QSplitter(Qt.Orientation.Horizontal)

        self.upper_left_frame = QFrame()
        self.upper_left_layout = QVBoxLayout()
        self.upper_right_frame = QFrame()
        self.upper_right_layout = QVBoxLayout()
        self.lower_left_frame = QFrame()
        self.lower_left_layout = QVBoxLayout()
        self.lower_right_frame = QFrame()
        self.lower_right_layout = QVBoxLayout()

        for frame in [
            self.upper_left_frame,
            self.upper_right_frame,
            self.lower_left_frame,
            self.lower_right_frame,
        ]:
            frame.setFrameStyle(QFrame.Box)
            frame.setLineWidth(1)

        self.upper_left_cb = QComboBox()
        self.upper_right_cb = QComboBox()
        self.lower_left_cb = QComboBox()
        self.lower_right_cb = QComboBox()

        self.upper_left_layout.addWidget(self.upper_left_cb)
        self.upper_right_layout.addWidget(self.upper_right_cb)
        self.lower_left_layout.addWidget(self.lower_left_cb)
        self.lower_right_layout.addWidget(self.lower_right_cb)

        self.upper_left_frame.setLayout(self.upper_left_layout)
        self.upper_right_frame.setLayout(self.upper_right_layout)
        self.lower_left_frame.setLayout(self.lower_left_layout)
        self.lower_right_frame.setLayout(self.lower_right_layout)

        self.splitter_vert_1.addWidget(self.upper_left_frame)
        self.splitter_vert_1.addWidget(self.upper_right_frame)
        self.splitter_vert_2.addWidget(self.lower_left_frame)
        self.splitter_vert_2.addWidget(self.lower_right_frame)

        self.splitter_hori.addWidget(self.splitter_vert_1)
        self.splitter_hori.addWidget(self.splitter_vert_2)
        self.layout().addWidget(self.splitter_hori)

    def setup_connections(self, client):
        client.livedata.connect(self.on_client_livedata)
        client.connected.connect(self.on_client_connected)

        self.splitter_vert_1.splitterMoved.connect(
            lambda x: self.splitter_moved(self.splitter_vert_1)
        )
        self.splitter_vert_2.splitterMoved.connect(
            lambda x: self.splitter_moved(self.splitter_vert_2)
        )

        self.upper_left_cb.currentIndexChanged.connect(
            lambda x: self._on_plot_changed(self.upper_left_cb, self.upper_left_layout)
        )
        self.upper_right_cb.currentIndexChanged.connect(
            lambda x: self._on_plot_changed(
                self.upper_right_cb, self.upper_right_layout
            )
        )
        self.lower_left_cb.currentIndexChanged.connect(
            lambda x: self._on_plot_changed(self.lower_left_cb, self.lower_left_layout)
        )
        self.lower_right_cb.currentIndexChanged.connect(
            lambda x: self._on_plot_changed(
                self.lower_right_cb, self.lower_right_layout
            )
        )

    @pyqtSlot()
    def _on_plot_changed(self, cb, layout):
        index = cb.currentIndex()
        current_plot_text = cb.currentText()
        for i in reversed(range(layout.count())):
            if layout.itemAt(i).widget() is cb:
                continue
            layout.itemAt(i).widget().deleteLater()

        if index == 0:
            return

        params, blobs = self.available_plots[current_plot_text]
        datadesc = params["datadescs"][0]
        shape = datadesc["shape"]
        if len(shape) == 1:
            view = LineView(parent=self)
            view.mode_checkbox.hide()
            view.clear_button.hide()
            view.log_checkbox.hide()
        elif len(shape) == 2:
            # would be nice to turn the histogram on the side in this plot
            view = ImageView(parent=self)
            view.splitter_vert_1.hide()
            view.bottom_plot.hide()
        else:
            return  # unsupported shape

        self._update_comboboxes()
        self.connected_plots[current_plot_text] = view
        layout.addWidget(view)
        view.show()

        self._on_plot_livedata(view, params, blobs)

    @pyqtSlot()
    def splitter_moved(self, sender):
        receiver = (
            self.splitter_vert_1
            if sender is self.splitter_vert_2
            else self.splitter_vert_2
        )
        receiver.blockSignals(True)
        receiver.setSizes(sender.sizes())
        receiver.blockSignals(False)

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

    def _on_plot_livedata(self, plot_widget, params, blobs):
        # do a bunch of data parsing

        data_shape = params["datadescs"][0]["shape"]
        label_shape = params["datadescs"][0].get("label_shape", [])
        data_dtype = params["datadescs"][0]["dtype"]
        # assume label_dtype is numpy float64 for now
        label_dtypes = params["datadescs"][0].get("label_dtypes")

        data = np.frombuffer(blobs[0], dtype=data_dtype).reshape(data_shape)
        labels = []
        for i, (shape, dtype) in enumerate(zip(label_shape, label_dtypes)):
            label = np.frombuffer(
                blobs[1][i * shape * 8 : (i + 1) * shape * 8], dtype=np.float64
            ).astype(dtype)
            labels.append(label)

        if len(data_shape) == 1 and isinstance(plot_widget, LineView):
            plot_widget.set_data([data], {"x": labels[0]})
        elif len(data_shape) == 2 and isinstance(plot_widget, ImageView):
            plot_widget.set_data([data], {"x": labels[0], "y": labels[1]})
        else:
            return

    def on_client_livedata(self, params, blobs):
        self.log.debug("on_client_livedata: %r", params)

        self.available_plots[params["det"]] = (params, blobs)
        self._update_comboboxes()

        # emit new data to any connected widgets
        selected_plot = self.connected_plots.get(params["det"], None)
        print(f"Slected plot: {selected_plot}")
        if selected_plot:
            self._on_plot_livedata(selected_plot, params, blobs)

        # blobs is a list of data blobs and labels blobs
        # if self._allowed_detectors and params["det"] not in self._allowed_detectors:
        #     return
        #
        # if params["tag"] == LIVE:
        #     datacount = len(params["datadescs"])
        #     for index, datadesc in enumerate(params["datadescs"]):
        #         labels, _ = process_axis_labels(datadesc, blobs[datacount:])
        #         for i, blob in enumerate(blobs[:datacount]):
        #             self._process_livedata(params, blob, index, labels)
        #
        #         if not datacount:
        #             self._process_livedata(params, [], 0, {})

    def _update_comboboxes(self):
        for cb in [
            self.upper_left_cb,
            self.upper_right_cb,
            self.lower_left_cb,
            self.lower_right_cb,
        ]:
            current_text = cb.currentText()
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("None")
            cb.addItems(self.available_plots.keys())
            new_index = cb.findText(current_text)
            if new_index:
                cb.setCurrentIndex(new_index)
            cb.blockSignals(False)

    def on_client_connected(self):
        self.client.tell("eventunmask", ["livedata"])
        # self.detectorskey = self._query_detectorskey()

    def _detectorskey(self):
        pass
        # if self.detectorskey is None:
        #     self.detectorskey = self._query_detectorskey()
        # return self.detectorskey

    def process_data_arrays(self, params, index, entry):
        """
        Check if the input 1D array has the expected amount of values.
        If the array is too small, a warning is raised.
        If the size exceeds the expected amount, it is truncated.
        Returns a list of arrays corresponding to the `plotcount` of
        `index` into `datadescs` of the current params.
        """
        pass
        # datadesc = params["datadescs"][index]
        # count = datadesc.get("plotcount", 1)
        # shape = datadesc["shape"]
        #
        # if self._liveOnlyIndex is not None and index != self._liveOnlyIndex:
        #     return
        #
        # arraysize = np.product(shape)
        #
        # if len(entry) != count * arraysize:
        #     self.log.warning(
        #         "Expected data array with %d entries, got %d",
        #         count * arraysize,
        #         len(entry),
        #     )
        #     return
        #
        # arrays = [
        #     entry[i * arraysize : (i + 1) * arraysize].reshape(shape)
        #     for i in range(count)
        # ]
        #
        # return arrays

    def _process_livedata(self, params, data, idx, labels):
        # ignore irrelevant data in liveOnly mode
        pass
        # if self._liveOnlyIndex is not None and idx != self._liveOnlyIndex:
        #     return
        # try:
        #     descriptions = params["datadescs"]
        # except KeyError:
        #     self.log.warning(
        #         'Livedata with tag "Live" without ' '"datadescs" provided.'
        #     )
        #     return
        #
        # # pylint: disable=len-as-condition
        # if len(data):
        #     # we got live data with specified formats
        #     arrays = self.process_data_arrays(
        #         params,
        #         idx,
        #         np.frombuffer(data, descriptions[idx]["dtype"]),
        #     )
        #
        #     if arrays is None:
        #         return
        #
        #     # cache and update displays
        #     if len(arrays[0].shape) == 1:
        #         if self.plotwidget.isVisible():
        #             self.plotwidget.hide()
        #         if not self.plotwidget_1d.isVisible():
        #             self.plotwidget_1d.show()
        #         self.plotwidget_1d.set_data(arrays, labels)
        #     else:
        #         if self.plotwidget_1d.isVisible():
        #             self.plotwidget_1d.hide()
        #         if not self.plotwidget.isVisible():
        #             self.plotwidget.show()
        #         self.plotwidget.set_data(arrays, [])

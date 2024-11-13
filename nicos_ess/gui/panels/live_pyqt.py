"""NICOS livewidget with pyqtgraph."""

from enum import Enum

import numpy as np

from nicos.clients.gui.panels import Panel
from nicos.core.constants import LIVE
from nicos.guisupport.livewidget import AXES, DATATYPES
from nicos.guisupport.qt import (
    QGroupBox,
    QScrollArea,
    QSize,
    QSplitter,
    Qt,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    pyqtProperty,
)

from nicos_ess.gui.widgets.pyqtgraph.line_view import LineView
from nicos_ess.gui.widgets.pyqtgraph.image_view import ImageView

TAB_WIDGET_MIN_WIDTH = 200
DEFAULT_TAB_WIDGET_MIN_WIDTH = 0
TAB_WIDGET_MAX_WIDTH = 200
DEFAULT_TAB_WIDGET_MAX_WIDTH = 16777215
VIEW_SPLITTER_SIZES = [600, 600, 100]


class LiveDataPanel(Panel):
    panelName = "Live data view"
    detectorskey = None
    _allowed_detectors = set()
    _liveOnlyIndex = None

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

        self.plotwidget = ImageView(parent=self)
        self.plotwidget_1d = LineView(parent=self)

        self.initialize_ui()
        self.build_ui()
        self.setup_connections(client)

    def initialize_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def build_ui(self):
        self.plotwidget.hide()
        self.plotwidget_1d.hide()
        self.view_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.view_splitter.addWidget(self.plotwidget)
        self.view_splitter.addWidget(self.plotwidget_1d)
        self.view_splitter.setStretchFactor(0, 1)
        self.view_splitter.setStretchFactor(1, 1)
        self.layout().addWidget(self.view_splitter)

        self.plotwidget.hide_roi_plotwidgets()

    def setup_connections(self, client):
        client.livedata.connect(self.on_client_livedata)
        client.connected.connect(self.on_client_connected)

    def normalize_type(self, dtype):
        normalized_type = np.dtype(dtype).str
        if normalized_type not in DATATYPES:
            self.log.warning("Unsupported live data format: %s", normalized_type)
            return
        return normalized_type

    def process_data_arrays(self, params, index, entry):
        """
        Check if the input 1D array has the expected amount of values.
        If the array is too small, a warning is raised.
        If the size exceeds the expected amount, it is truncated.
        Returns a list of arrays corresponding to the `plotcount` of
        `index` into `datadescs` of the current params.
        """

        datadesc = params["datadescs"][index]
        count = datadesc.get("plotcount", 1)
        shape = datadesc["shape"]

        if self._liveOnlyIndex is not None and index != self._liveOnlyIndex:
            return

        arraysize = np.product(shape)

        if len(entry) != count * arraysize:
            self.log.warning(
                "Expected data array with %d entries, got %d",
                count * arraysize,
                len(entry),
            )
            return

        arrays = [
            entry[i * arraysize : (i + 1) * arraysize].reshape(shape)
            for i in range(count)
        ]

        return arrays

    def _process_livedata(self, params, data, idx, labels):
        # ignore irrelevant data in liveOnly mode
        if self._liveOnlyIndex is not None and idx != self._liveOnlyIndex:
            return
        try:
            descriptions = params["datadescs"]
        except KeyError:
            self.log.warning(
                'Livedata with tag "Live" without ' '"datadescs" provided.'
            )
            return

        # pylint: disable=len-as-condition
        if len(data):
            # we got live data with specified formats
            arrays = self.process_data_arrays(
                params,
                idx,
                np.frombuffer(data, descriptions[idx]["dtype"]),
            )

            if arrays is None:
                return

            # cache and update displays
            if len(arrays[0].shape) == 1:
                if self.plotwidget.isVisible():
                    self.plotwidget.hide()
                if not self.plotwidget_1d.isVisible():
                    self.plotwidget_1d.show()
                self.plotwidget_1d.set_data(arrays, labels)
            else:
                if self.plotwidget_1d.isVisible():
                    self.plotwidget_1d.hide()
                if not self.plotwidget.isVisible():
                    self.plotwidget.show()
                self.plotwidget.set_data(arrays, [])

    def update_widget_to_show(self, is_2d):
        if is_2d:
            if self.plotwidget_1d.isVisible():
                self.plotwidget_1d.hide()
            if not self.plotwidget.isVisible():
                self.plotwidget.show()
        else:
            if self.plotwidget.isVisible():
                self.plotwidget.hide()
            if not self.plotwidget_1d.isVisible():
                self.plotwidget_1d.show()

    def exec_command(self, command):
        self.client.tell("exec", command)

    def eval_command(self, command, *args, **kwargs):
        return self.client.eval(command, *args, **kwargs)

    def on_client_livedata(self, params, blobs):
        self.log.debug("on_client_livedata: %r", params)
        # blobs is a list of data blobs and labels blobs
        if self._allowed_detectors and params["det"] not in self._allowed_detectors:
            return

        if params["tag"] == LIVE:
            datacount = len(params["datadescs"])
            for index, datadesc in enumerate(params["datadescs"]):
                labels, _ = process_axis_labels(datadesc, blobs[datacount:])
                for i, blob in enumerate(blobs[:datacount]):
                    self._process_livedata(params, blob, index, labels)

                if not datacount:
                    self._process_livedata(params, [], 0, {})

    def on_client_connected(self):
        self.client.tell("eventunmask", ["livedata"])
        self.detectorskey = self._query_detectorskey()

    def _detectorskey(self):
        if self.detectorskey is None:
            self.detectorskey = self._query_detectorskey()
        return self.detectorskey

    def _query_detectorskey(self):
        try:
            return ("%s/detlist" % self.client.eval("session.experiment.name")).lower()
        except AttributeError:
            pass


class State(Enum):
    UNSELECTED = 0
    SELECTED = 1


class LiveWidgetWrapper(QGroupBox):
    def __init__(self, title, widget, parent=None):
        QGroupBox.__init__(self, title=title, parent=parent)
        self.state = State.UNSELECTED
        self.parent = parent

        self.setContentsMargins(0, 0, 0, 0)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 5, 0, 0)
        self.setLayout(vbox)
        self.layout().addWidget(widget)

    def widget(self):
        return self.layout().itemAt(0).widget()

    def resizeEvent(self, event):
        # Maintain aspect ratio when resizing
        width = int(self.parent.tab_widget.sizeHint().width() * 0.9)
        new_size = QSize(width, width)
        self.resize(new_size)
        self.setMinimumHeight(width)

    @pyqtProperty(str)
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value.name
        self.refresh_widget()

    def refresh_widget(self):
        """
        Update the widget with a new stylesheet.
        """
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


def layout_iterator(layout):
    return (layout.itemAt(i) for i in range(layout.count()))


def get_detectors_in_layout(layout):
    return [item.widget().name for item in layout_iterator(layout)]


def process_axis_labels(datadesc, blobs, offset=0):
    """Convert the raw axis label descriptions.
    Similar to LiveDataPanel._process_axis_labels, but is flexible in datadesc.
    """
    CLASSIC = {"define": "classic"}
    labels = {}
    titles = {}
    for size, axis in zip(reversed(datadesc["shape"]), AXES):
        # if the 'labels' key does not exist or does not have the right
        # axis key set default to 'classic'.
        label = datadesc.get("labels", {"x": CLASSIC, "y": CLASSIC}).get(axis, CLASSIC)
        if label["define"] == "range":
            start = label.get("start", 0)
            size = label.get("length", 1)
            step = label.get("step", 1)
            end = start + step * size
            labels[axis] = np.arange(start, end, step)
        elif label["define"] == "array":
            index = label.get("index", 0)
            labels[axis] = np.frombuffer(blobs[index], label.get("dtype", "<i4"))
        else:
            labels[axis] = np.array(range(size))
        labels[axis] += offset if axis == "x" else 0
        titles[axis] = label.get("title")

    return labels, titles


def process_data_arrays(index, params, data):
    """Returns a list of arrays corresponding to the ``count`` of
    ``index`` into ``datadescs`` of the current params"""
    datadesc = params["datadescs"][index]
    count = datadesc.get("count", 1)
    shape = datadesc["shape"]

    # determine 1D array size
    arraysize = np.product(shape)
    arrays = np.split(data[: count * arraysize], count)

    # reshape every array in the list
    for i, array in enumerate(arrays):
        arrays[i] = array.reshape(shape)
    return arrays


def process_livedata(widget, data, params, labels, idx):
    descriptions = params["datadescs"]

    # pylint: disable=len-as-condition
    if len(data):
        arrays = process_data_arrays(
            idx,
            params,
            np.frombuffer(data, descriptions[idx]["dtype"]),
        )
        if arrays is None:
            return
        widget.set_data(arrays, labels)


class DetContainer:
    """
    Container class for items related to a detector.
    """

    def __init__(self, name):
        self.name = name
        self._params_cache = {}
        self._blobs_cache = []
        self._previews_to_index = {}
        self._blobs_to_index = {}
        self._previews = []

    def add_preview(self, name):
        self._previews_to_index[name] = len(self._previews)
        self._previews.append(name)

    def update_cache(self, params, blobs):
        self._params_cache = params
        self._blobs_cache = blobs

    def update_blobs_to_index(self, name):
        if not self._params_cache:
            return

        self._blobs_to_index[name] = [self._previews_to_index[name]]
        for idx, datadesc in enumerate(self._params_cache["datadescs"]):
            transferred_label_count = self._previews_to_index[name]
            for axis in datadesc["labels"].values():
                if axis["define"] != "classic":
                    transferred_label_count += 1
                    self._blobs_to_index[name].append(transferred_label_count)

    def get_preview_name(self, index):
        return self._previews[index]

    def get_preview_data(self, name):
        self.update_blobs_to_index(name)
        ch = self._previews_to_index[name]
        if self._params_cache and self._blobs_cache:
            params = dict(self._params_cache)
            params["datadescs"] = [params["datadescs"][ch]]
            idx = self._blobs_to_index[name]
            return params, [*self._blobs_cache[idx[0] : idx[-1] + 1]]
        return None, None


class Preview:
    """
    Container class for items related to a preview.
    """

    def __init__(self, name, detector, widget):
        """
        :param name: name of the preview
        :param detector: the detector the preview belongs to
        :param widget: the preview widget.
        """
        self.name = name
        self.detector = detector
        self._widget = widget
        self._savestate = {}

    @property
    def widget(self):
        return self._widget.widget()

    def show(self):
        self._widget.state = State.SELECTED

    def hide(self):
        self._widget.state = State.UNSELECTED


class MultiLiveDataPanel(LiveDataPanel):
    """
    MultiLiveDataPanel is a class that extends the LiveDataPanel to handle
    multiple detectors and previews. It provides functionality for creating
    and managing detector previews, updating and displaying live data, and
    switching between 1D and 2D data views.
    The MultiLiveDataPanel shows all the detectors in a side area.
    Each detector can be set as the one to be displayed in the main plot with a
    click on it.
    Options:
    * ``default_detector`` -- the default detector to be displayed in the main
    widget
    """

    panelName = "MultidetectorLiveDataView"

    def __init__(self, parent, client, options):
        self._detector_selected = options.get("default_detector", "")
        self._detectors = {}
        self._previews = {}
        self._plotwidget_settings = {}
        LiveDataPanel.__init__(self, parent, client, options)

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.tab_widget = QTabWidget()
        self.widget_container = QWidget()
        self.tab_layout = QVBoxLayout()

        self.tab_widget.setTabBarAutoHide(True)
        self.widget_container.setLayout(self.tab_layout)

        self.scroll_content = QWidget()
        self.scroll_content.setLayout(QVBoxLayout())

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.scroll_content)
        self.tab_widget.addTab(self.scroll, "Previews")
        self.tab_widget.addTab(self.plotwidget.image_view_controller, "View Settings")
        self.set_tab_widget_width()
        self.set_scroll_area_width()
        self.scroll.setWidgetResizable(True)

        self.tab_layout.addWidget(
            self.plotwidget.image_view_controller.hist_autoscale_btn
        )
        self.tab_layout.addWidget(self.tab_widget)

        self.view_splitter.addWidget(self.widget_container)
        self.view_splitter.setSizes(VIEW_SPLITTER_SIZES)
        self.view_splitter.setStretchFactor(0, 1)
        self.view_splitter.setStretchFactor(1, 1)
        self.view_splitter.setStretchFactor(2, 0)

    def set_tab_widget_width(self):
        width = self.tab_widget.sizeHint().width()
        self.tab_widget.setMinimumWidth(width)

    def set_scroll_area_width(self):
        width = self.tab_widget.sizeHint().width()
        self.scroll.setMinimumWidth(width)

    def connect_signals(self):
        self.connect_disconnected_signal()
        self.connect_setup_signal()
        self.connect_cache_signal()

        self.connect_histogram_signals()
        self.connect_plotwidget_1d_signals()

    def save_plotsettings(self, is_2d):
        widget_name = self.get_widget_name(is_2d)
        if not widget_name:
            return

        plot_settings = self.get_plot_settings(is_2d)
        self._plotwidget_settings[widget_name] = plot_settings

    def restore_plotsettings(self, is_2d):
        widget_name = self.get_widget_name(is_2d)
        if widget_name not in self._plotwidget_settings:
            return

        plot_settings = self._plotwidget_settings[widget_name]
        self.apply_plot_settings(is_2d, plot_settings)

    def apply_plot_settings(self, is_2d, plot_settings):
        if is_2d:
            self.plotwidget.restore_state(plot_settings)
        else:
            pass

    def get_widget_name(self, is_2d):
        if is_2d:
            return self.plotwidget.name
        else:
            return self.plotwidget_1d.name

    def get_plot_settings(self, is_2d):
        if is_2d:
            return self.plotwidget.save_state()
        else:
            return self.plotwidget_1d.save_state()

    def connect_disconnected_signal(self):
        self.client.disconnected.connect(self.on_client_disconnected)

    def connect_setup_signal(self):
        self.client.setup.connect(self.on_client_setup)

    def connect_cache_signal(self):
        self.client.cache.connect(self.on_client_cache)

    def connect_histogram_signals(self):
        self.plotwidget.settings_histogram.item.sigLookupTableChanged.connect(
            self.lut_changed
        )
        self.plotwidget.settings_histogram.item.sigLevelsChanged.connect(
            self.levels_changed
        )

    def connect_plotwidget_1d_signals(self):
        self.plotwidget_1d.clear_button.clicked.connect(self.plot_clear_data)
        self.plotwidget_1d.mode_checkbox.stateChanged.connect(self.plot_mode_changed)
        self.plotwidget_1d.log_checkbox.stateChanged.connect(self.plot_log_mode_changed)
        self.plotwidget_1d.vertical_line.sigPositionChangeFinished.connect(
            self.plot_vertical_line_changed
        )

    def update_previews(self, action, widget_name):
        for name, preview in self._previews.items():
            if preview.widget.name == widget_name:
                action(preview)

    def plot_mode_changed(self):
        current_plot_mode = self.plotwidget_1d.mode_checkbox.isChecked()
        self.update_previews(
            lambda preview: preview.widget.mode_checkbox.setChecked(current_plot_mode),
            self.plotwidget_1d.name,
        )

    def plot_clear_data(self):
        self.update_previews(
            lambda preview: preview.widget.clear_data(), self.plotwidget_1d.name
        )

    def plot_log_mode_changed(self):
        current_log_mode = self.plotwidget_1d.log_checkbox.isChecked()
        self.update_previews(
            lambda preview: preview.widget.log_checkbox.setChecked(current_log_mode),
            self.plotwidget_1d.name,
        )

    def plot_vertical_line_changed(self):
        current_value = self.plotwidget_1d.vertical_line.value()
        self.update_previews(
            lambda preview: preview.widget.vertical_line.setValue(current_value),
            self.plotwidget_1d.name,
        )

    def lut_changed(self):
        current_gradient_state = (
            self.plotwidget.settings_histogram.item.gradient.saveState()
        )
        self.update_previews(
            lambda preview: preview.widget.settings_histogram.item.gradient.restoreState(
                current_gradient_state
            ),
            self.plotwidget.name,
        )

    def levels_changed(self):
        current_image_levels = self.plotwidget.image_item.getLevels()
        self.update_previews(
            lambda preview: preview.widget.image_item.setLevels(current_image_levels),
            self.plotwidget.name,
        )

    def on_1d_data_changed(self, state):
        self.plotwidget_1d.clear_data()
        self.plotwidget_1d.restore_state(state)

    def on_client_connected(self):
        LiveDataPanel.on_client_connected(self)
        self._cleanup_existing_previews()
        if not self._previews:
            self._populate_previews()

    def on_client_disconnected(self):
        self._cleanup_existing_previews()

    def _cleanup_existing_previews(self):
        for item in layout_iterator(self.scroll_content.layout()):
            item.widget().deleteLater()
            del item
        self._previews.clear()
        self._detectors.clear()

    def create_previews_for_detector(self, det_name):
        previews = self.create_preview_widgets(det_name)
        self.add_previews_to_layout(previews, det_name)

    def add_previews_to_layout(self, previews, det_name):
        for preview in previews:
            name = preview.widget().name
            self._previews[name] = Preview(name, det_name, preview)
            self._detectors[det_name].add_preview(name)
            preview.widget().clicked.connect(self.on_preview_clicked)
            self.scroll_content.layout().addWidget(preview)

    def on_client_setup(self):
        self._cleanup_existing_previews()
        if not self._previews:
            self._populate_previews()

    def highlight_selected_preview(self, selected):
        for name, preview in self._previews.items():
            if name == selected:
                preview.show()
            else:
                preview.hide()

    def _populate_previews(self):
        detectors = set(self.find_detectors())
        if not detectors:
            return
        self.add_detectors_to_previews(detectors)
        self._display_first_detector()

    def add_detectors_to_previews(self, detectors):
        for detector in detectors:
            self._detectors[detector] = DetContainer(detector)
            self.create_previews_for_detector(detector)

    def _display_first_detector(self):
        if self._previews:
            first_preview = next(iter(self._previews.values()))
            self.display_preview(first_preview)

    def display_preview(self, preview):
        preview.widget.clicked.emit(preview.name)
        if isinstance(preview.widget, LineView):
            self.plotwidget_1d.name = preview.name
        elif isinstance(preview.widget, ImageView):
            self.plotwidget.name = preview.name

    def on_client_cache(self, data):
        _, key, _, _ = data
        if key == "exp/detlist":
            self._cleanup_existing_previews()

    def on_client_livedata(self, params, blobs):
        det_name = params["det"]

        if not self._previews:
            self._populate_previews()

        self.set_preview_data(params, blobs)
        self.update_selected_main_widget(det_name)

    def update_selected_main_widget(self, det_name):
        if not self._detector_selected or self._detector_selected not in self._previews:
            return

        if self._previews[self._detector_selected].detector == det_name:
            pars, blob = self._detectors[det_name].get_preview_data(
                self._detector_selected
            )
            LiveDataPanel.on_client_livedata(self, pars, blob)

    def find_detectors(self):
        return self._get_configured_detectors()

    def _get_configured_detectors(self):
        state = self.client.ask("getstatus")
        if not state:
            return []
        detlist = self.client.getCacheKey("exp/detlist")
        if not detlist:
            return []
        return [det for det in detlist[1] if self.client.eval(f"{det}.arrayInfo()", [])]

    def create_preview_widgets(self, det_name):
        array_info = self.client.eval(f"{det_name}.arrayInfo()", ())
        previews = [self._create_preview_widget(info) for info in array_info]
        return previews

    def _create_preview_widget(self, info):
        if len(info.shape) == 1:
            return self._create_line_view_preview_widget(info)
        else:
            return self._create_image_view_preview_widget(info)

    def _create_line_view_preview_widget(self, info):
        widget = LineView(name=info.name, parent=self, preview_mode=True)
        widget.view.setMouseEnabled(False, False)
        widget.plot_widget.getPlotItem().hideAxis("bottom")
        widget.plot_widget.getPlotItem().hideAxis("left")
        widget.plot_widget_sliced.hide()
        widget.data_changed.connect(self.on_1d_data_changed)
        return LiveWidgetWrapper(title=info.name, widget=widget, parent=self)

    def _create_image_view_preview_widget(self, info):
        widget = ImageView(name=info.name, parent=self)
        widget.view.setMouseEnabled(False, False)
        widget.splitter_hori_1.setHandleWidth(0)
        widget.image_view_controller.hide()
        widget.settings_histogram.hide()
        widget.hover_label.hide()
        widget.hide_roi(ignore_connections=True)
        widget.hide_crosshair_roi(ignore_connections=True)
        widget.hide_roi_plotwidgets()
        return LiveWidgetWrapper(title=info.name, widget=widget, parent=self)

    def set_preview_data(self, params, blobs):
        self._update_and_process_preview_data(params, blobs)

    def _update_and_process_preview_data(self, params, blobs):
        parent = params["det"]
        if parent not in self._detectors:
            self.log.warning(f"Detector {parent} not found in detectors")
            return
        self._detectors[parent].update_cache(params, blobs)
        datacount = len(params["datadescs"])

        for index, datadesc in enumerate(params["datadescs"]):
            normalized_type = self.normalize_type(datadesc["dtype"])
            name = self._detectors[parent].get_preview_name(index)
            widget = self._previews[name].widget
            labels, _ = process_axis_labels(datadesc, blobs[datacount:])
            if self._has_plot_changed_dimensionality(widget, labels):
                self._cleanup_existing_previews()
                return
            process_livedata(
                widget,
                np.frombuffer(blobs[index], normalized_type),
                params,
                labels,
                index,
            )

    def _has_plot_changed_dimensionality(self, widget, labels):
        return (isinstance(widget, LineView) and "y" in labels) or (
            not isinstance(widget, LineView) and "y" not in labels
        )

    def on_preview_clicked(self, det_name):
        self._change_detector_to_display(det_name)

    def _change_detector_to_display(self, det_name):
        self._detector_selected = det_name
        parent = self._previews[det_name].detector
        if parent not in self._detectors:
            self.log.warning(f"Detector {parent} not found in detectors")
            return
        pars, blob = self._detectors[parent].get_preview_data(self._detector_selected)
        is_2d = isinstance(self._previews[det_name].widget, ImageView)
        switched_plot = self._check_switched_plot(det_name, is_2d)

        self.save_plotsettings(is_2d=is_2d)
        self._update_plot_widget_name(det_name, is_2d)
        if switched_plot:
            self._handle_switched_plot(det_name, is_2d, pars, blob)

        self.highlight_selected_preview(det_name)

    def _check_switched_plot(self, det_name, is_2d):
        if self.plotwidget.isVisible() and not is_2d:
            return True
        elif self.plotwidget_1d.isVisible() and is_2d:
            return True
        elif is_2d:
            return det_name != self.plotwidget.name
        else:
            return det_name != self.plotwidget_1d.name

    def _update_plot_widget_name(self, det_name, is_2d):
        if is_2d:
            self.plotwidget.view.enableAutoRange()
            self.plotwidget.name = det_name
        else:
            self.plotwidget_1d.view.enableAutoRange()
            self.plotwidget_1d.name = det_name

    def _handle_switched_plot(self, det_name, is_2d, pars, blob):
        self.restore_plotsettings(is_2d=is_2d)
        if is_2d:
            if pars and blob:
                LiveDataPanel.on_client_livedata(self, pars, blob)
        else:
            self.plotwidget_1d.clear_data()
            preview_state = self._previews[det_name].widget.save_state()
            self.plotwidget_1d.restore_state(preview_state)
            LiveDataPanel.update_widget_to_show(self, is_2d=is_2d)

    def on_closed(self):
        self._clear_previews()
        LiveDataPanel.on_closed(self)

    def _clear_previews(self):
        for item in layout_iterator(self.scroll_content.layout()):
            item.widget().deleteLater()
            del item

import os.path as osp
from weakref import WeakKeyDictionary

import numpy as np

from nicos.guisupport.qt import (
    QFileDialog, pyqtSlot, pyqtSignal, QMainWindow, QWidget, QVBoxLayout, QPushButton)

from nicos.clients.flowui.panels import get_icon
from nicos.clients.flowui.panels.live import LiveDataPanel as DefaultLiveDataPanel
from nicos_mlz.toftof.gui.resolutionpanel import PlotWidget


class LiveDataPanel(DefaultLiveDataPanel):
    ui = f"{osp.dirname(__file__)}/ui_files/live.ui"
    refresh_snap_shot_data = pyqtSignal()

    def __init__(self, parent, client, options):
        DefaultLiveDataPanel.__init__(self, parent, client, options)
        self.last_save_location = None
        self.background_data = None

        self.refresh_snap_shot_data.connect(self._refresh_snap_shot_window)
        self._registered_windows = WeakKeyDictionary()
        self.setControlsEnabled(False)

    def createPanelToolbar(self):
        toolbar = DefaultLiveDataPanel.createPanelToolbar(self)
        toolbar.addSeparator()
        toolbar.addAction(self.actionSaveData)
        toolbar.addAction(self.actionSubtractBackground)
        return toolbar

    def set_icons(self):
        DefaultLiveDataPanel.set_icons(self)
        self.actionSaveData.setIcon(get_icon("archive-24px.svg"))

    @pyqtSlot()
    def on_snapShotButton_clicked(self):
        if self.checkWindowOpen(SnapShotWindow, self._registered_windows):
            # self._refresh_snap_shot_window()
            return
        self._snapshot_window = SnapShotWindow(self)
        self._refresh_snap_shot_window()
        return self._snapshot_window

    def _refresh_snap_shot_window(self):
        current_blob = self._extract_data()
        if current_blob:
            data = current_blob.get("dataarrays", [])[0]
            labels = current_blob.get("labels", {})
            self._snapshot_window.setData(labels, data)

    @pyqtSlot()
    def on_actionSaveData_triggered(self):
        self.export_data_to_file()

    def export_data_to_file(self):
        filename = QFileDialog.getSaveFileName(
            self,
            "Save image",
            osp.expanduser("~")
            if self.last_save_location is None
            else self.last_save_location,
            "Numpy binary files (*.npy)",
            initialFilter="*.npy",
        )[0]

        if not filename:
            return
        if not filename.endswith(".npy"):
            filename = filename + ".npy"

        self.last_save_location = osp.dirname(filename)

        data_arrays = self._extract_data().get("dataarrays", [])

        if data_arrays:
            with open(filename, "w") as f:
                np.save(osp.abspath(f.name), np.array(data_arrays[0]))
        else:
            self.showError(f"No data available for writing to {filename}")

    def _extract_data(self):
        if self.fileList.currentRow() == -1:
            return
        # try to get data from the cache
        data = self.getDataFromItem(self.fileList.currentItem())
        return data

    def registerWindow(self, instance):
        """Register an instance of a QMainWindow"""
        self._registered_windows[instance] = 1

    def unregisterWindow(self, instance):
        """De-Register an instance if closeEvent is called"""
        if instance in self._registered_windows:
            del self._registered_windows[instance]

    def checkWindowOpen(self, instance, windows):
        """Check if window is already open, then bring it to front"""
        for window in windows:
            if isinstance(window, instance):
                window.activateWindow()
                return True
        return False


class SnapShotWindow(QMainWindow):
    """AboutWindow class"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Snapshot")

        if parent is not None:
            parent.registerWindow(self)

        self._central_widget = QWidget()
        self._test = QWidget()
        self._data = None

        self._plot =  PlotWidget(
            "Test", "xlabel", "ylabel", ncurves=2, parent=self._test)

        self.updateDataButton = QPushButton("Update")
        self.updateDataButton.clicked.connect(self.on_updateDataButton_clicked)

        self.setupUi()
        self.setCentralWidget(self._central_widget)
        self.setFixedSize(660, 500)
        self.show()

    def setupUi(self):
        layout = QVBoxLayout()

        layout.addWidget(self._test)
        layout.addWidget(self.updateDataButton)
        self._central_widget.setLayout(layout)

    @pyqtSlot()
    def on_updateDataButton_clicked(self):
        self.parent().refresh_snap_shot_data.emit()

    def closeEvent(self, QCloseEvent):
        if self.parent() is not None:
            self.parent().unregisterWindow(self)
        super().closeEvent(QCloseEvent)

    def setData(self, labels, data):
        if len(data.shape) == 1:
            self._plot.setData(labels['x'], data)

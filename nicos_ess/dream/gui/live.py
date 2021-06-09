import os.path as osp
from weakref import WeakKeyDictionary

import numpy as np

from nicos.clients.flowui.panels import get_icon
from nicos.clients.flowui.panels.live import \
    LiveDataPanel as DefaultLiveDataPanel
from nicos.guisupport.qt import QFileDialog, pyqtSignal, pyqtSlot

from nicos_ess.dream.gui.snap_shot_window import SnapShotWindow


class LiveDataPanel(DefaultLiveDataPanel):
    ui = f"{osp.dirname(__file__)}/ui_files/live.ui"
    update_background_data = pyqtSignal()

    def __init__(self, parent, client, options):
        DefaultLiveDataPanel.__init__(self, parent, client, options)
        self.last_save_location = None
        self.setControlsEnabled(False)

        self.update_background_data.connect(self._set_background_data)
        self._registered_windows = WeakKeyDictionary()
        self._snapshot_window = None

        client.livedata.connect(self.on_live_data_update)

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
            # self._set_background_data()
            return
        self._snapshot_window = SnapShotWindow(self)
        self._set_background_data()
        return self._snapshot_window

    def _set_background_data(self):
        data, labels = self._extract_data()
        # Deal with 1D data only for the timebeing
        if data and len(data[0].shape) == 1:
            self._snapshot_window.background_data = data[0]
            self._snapshot_window.setData(labels, None)

    def on_live_data_update(self):
        data, labels = self._extract_data()
        # Deal with 1D data only for the timebeing
        if data and len(data[0].shape) == 1:
            if self._snapshot_window:
                self._snapshot_window.setData(labels, data[0])

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

        data, _ = self._extract_data()

        if data:
            with open(filename, "w") as f:
                np.save(osp.abspath(f.name), np.array(data[0]))
        else:
            self.showError(f"No data available for writing to {filename}")

    def _extract_data(self):
        if self.fileList.currentRow() == -1:
            self.fileList.setCurrentRow(0)
        # try to get data from the cache
        current_blob = self.getDataFromItem(self.fileList.currentItem())
        if not current_blob:
            return None, None

        data = current_blob.get("dataarrays", [])
        labels = current_blob.get("labels", {})
        return data, labels

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

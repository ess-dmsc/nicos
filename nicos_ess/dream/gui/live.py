import os.path as osp
from datetime import datetime
from os import path
from uuid import uuid4
from weakref import WeakKeyDictionary

import numpy as np

from nicos.clients.flowui.panels import get_icon
from nicos.clients.flowui.panels.live import \
    LiveDataPanel as DefaultLiveDataPanel
from nicos.clients.gui.panels.live import FILENAME, FILEUID
from nicos.guisupport.qt import QFileDialog, pyqtSignal, pyqtSlot
from nicos.utils import BoundedOrderedDict

from nicos_ess.dream.gui.comparison_window import ComparisonWindow

SNAP = 'snap'


class LiveDataPanel(DefaultLiveDataPanel):
    ui = f"{osp.dirname(__file__)}/ui_files/live.ui"
    update_background_data = pyqtSignal()

    def __init__(self, parent, client, options):
        DefaultLiveDataPanel.__init__(self, parent, client, options)
        self.last_save_location = None
        self.setControlsEnabled(False)

        self.update_background_data.connect(self._set_background_data)
        self._registered_windows = WeakKeyDictionary()
        self._compare_window = None

        self._snap_cache = BoundedOrderedDict(maxlen=10)
        client.livedata.connect(self.on_live_data_update)

    def createPanelToolbar(self):
        toolbar = DefaultLiveDataPanel.createPanelToolbar(self)
        toolbar.addSeparator()
        toolbar.addAction(self.actionSaveData)
        return toolbar

    def set_icons(self):
        DefaultLiveDataPanel.set_icons(self)
        self.actionSaveData.setIcon(get_icon("archive-24px.svg"))

    @pyqtSlot()
    def on_compareButton_clicked(self):
        if self.checkWindowOpen(ComparisonWindow, self._registered_windows):
            return
        self._compare_window = ComparisonWindow(self)
        self._set_background_data()
        return self._compare_window

    def _set_background_data(self):
        # Deal with 1D data only for the timebeing
        data = self._get_1d_data()
        if data:
            self._compare_window.setData(None, background_data_blob=data)

    def on_live_data_update(self):
        # Deal with 1D data only for the timebeing
        data = self._get_1d_data()
        if data and self._compare_window:
            self._compare_window.setData(data)

    def _get_1d_data(self):
        data, labels = self._extract_data()
        if data and len(data[0].shape) == 1:
            return labels, data[0]
        return

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

    @pyqtSlot()
    def on_snapShotButton_clicked(self):
        data, labels = self._extract_data()
        if not data:
            return
        uid = uuid4()
        self._snap_cache[uid] = {}
        self._snap_cache[uid]['dataarrays'] = data
        self._snap_cache[uid]['labels'] = labels
        self.add_to_flist(
            f'snapshot_{datetime.now()}', '', SNAP, uid)

    def getDataFromItem(self, item):
        if item is None:
            return

        uid = item.data(FILEUID)
        if uid and hasattr(self, '_snap_cache') and uid in self._snap_cache:
            return self._snap_cache[uid]
        else:
            return DefaultLiveDataPanel.getDataFromItem(self, item)

    def remove_obsolete_cached_files(self):
        """Override"""
        for index in reversed(range(self.fileList.count())):
            item = self.fileList.item(index)
            uid = item.data(FILEUID)
            # is the uid still cached
            if uid and uid not in self._datacache and uid not in self._snap_cache:
                # does the file still exist on the filesystem
                if path.isfile(item.data(FILENAME)):
                    item.setData(FILEUID, None)
                else:
                    self.fileList.takeItem(index)

import os.path as osp

import numpy as np

from nicos.guisupport.qt import QFileDialog, Qt, QToolBar, pyqtSlot

from nicos_ess.gui.panels import get_icon
from nicos_ess.gui.panels.live import LiveDataPanel as DefaultLiveDataPanel


class LiveDataPanel(DefaultLiveDataPanel):
    ui = f"{osp.dirname(__file__)}/ui_files/live.ui"

    def __init__(self, parent, client, options):
        DefaultLiveDataPanel.__init__(self, parent, client, options)
        self.last_save_location = None
        self.background_data = None

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

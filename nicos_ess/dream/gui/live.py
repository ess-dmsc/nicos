from nicos_ess.gui.panels.live import LiveDataPanel as DefaultLiveDataPanel
from nicos.guisupport.qt import QToolBar, pyqtSlot, QFileDialog, Qt
from nicos_ess.gui.panels import get_icon

import numpy as np
import os.path as osp
FILEUID = Qt.UserRole + 3

class LiveDataPanel(DefaultLiveDataPanel):
    ui = f'{osp.dirname(__file__)}/ui_files/live.ui'

    def __init__(self, parent, client, options):
        DefaultLiveDataPanel.__init__(self, parent, client, options)
        self.last_save_location = None
        self.background_data = None

        self.setControlsEnabled(False)

    def createPanelToolbar(self):
        toolbar = QToolBar('Live data')
        toolbar.addAction(self.actionOpen)
        toolbar.addAction(self.actionPrint)
        toolbar.addAction(self.actionSavePlot)
        toolbar.addSeparator()
        toolbar.addAction(self.actionSaveData)
        toolbar.addAction(self.actionSubtractBackground)
        toolbar.addSeparator()
        toolbar.addAction(self.actionLogScale)
        toolbar.addSeparator()
        toolbar.addAction(self.actionKeepRatio)
        toolbar.addAction(self.actionUnzoom)
        toolbar.addAction(self.actionColormap)
        toolbar.addAction(self.actionMarkCenter)
        toolbar.addAction(self.actionROI)
        return toolbar

    def set_icons(self):
        self.actionPrint.setIcon(get_icon('print-24px.svg'))
        self.actionSavePlot.setIcon(get_icon('save-24px.svg'))
        self.actionSaveData.setIcon(get_icon('archive-24px.svg'))
        self.actionUnzoom.setIcon(get_icon('zoom_out-24px.svg'))
        self.actionOpen.setIcon(get_icon('folder_open-24px.svg'))

    @pyqtSlot()
    def on_actionSaveData_triggered(self):
        self.export_data_to_file()

    def export_data_to_file(self):
        filename = QFileDialog.getSaveFileName(
            self,
            'Save Data',
            osp.expanduser('~') if self.last_save_location is None
            else self.last_save_location,
            'Data files (*.npy)',
            initialFilter='*.npy')[0]

        if not filename:
            return
        if not filename.endswith(('.npy')):
            filename = filename + '.npy'

        self.last_save_location = osp.dirname(filename)

        data_arrays = self._extract_data().get('dataarrays', [])

        if data_arrays:
            with open(filename, "w") as f:
                np.save(osp.abspath(f.name), np.array(data_arrays[0]))
        else:
            self.showError(f'No data available for writing to {filename}')

    def _extract_data(self):
        if self.fileList.currentRow() == -1:
            return

        # try to get data from the cache
        data = self.getDataFromItem(self.fileList.currentItem())
        # no data
        if data is None:
            return

        return data

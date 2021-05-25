from nicos_ess.gui.panels.live import LiveDataPanel as DefaultLiveDataPanel
from nicos.guisupport.qt import QListWidget, QToolBar, pyqtSlot, QFileDialog
from nicos_ess.gui.panels import get_icon

import numpy as np
import os.path as osp


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
        toolbar.addAction(self.actionLoadData)
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
        self.actionLoadData.setIcon(get_icon('add-24px.svg'))
        self.actionUnzoom.setIcon(get_icon('zoom_out-24px.svg'))
        self.actionOpen.setIcon(get_icon('folder_open-24px.svg'))

    @pyqtSlot()
    def on_actionSaveData_triggered(self):
        self.export_data_to_file()

    @pyqtSlot()
    def on_actionLoadData_triggered(self):
        self.import_data_from_file()

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

        data_arrays = self._extract_data()
        if data_arrays:
            with open(filename, "w") as f:
                np.save(osp.abspath(f.name), np.array(data_arrays))
        else:
            self.showError(f'No data available for writing to {filename}')

    def _extract_data(self):
        idx = self.fileList.currentRow()
        if idx == -1:
            self.fileList.setCurrentRow(0)
            return

        # try to get data from the cache
        data = self.getDataFromItem(self.fileList.currentItem())
        # no data
        if data is None:
            return

        arrays = data.get('dataarrays', [])
        return arrays

    def import_data_from_file(self):
        try:
            filename = QFileDialog.getOpenFileName(
                self,
                'Open Data',
                osp.expanduser('~') if self.last_save_location is None \
                    else self.last_save_location,
                'Data Files (*.npy)')[0]

            if not filename:
                return

            self.background_data = np.load(filename)
        except Exception as error:
            self.log.warn(f"Cannot import data from file: {filename}")

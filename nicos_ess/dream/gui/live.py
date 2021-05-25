from nicos_ess.gui.panels.live import MultiLiveDataPanel as DefaultMultiLiveDataPanel
from nicos.guisupport.qt import pyqtSlot, QFileDialog

import numpy as np
import os.path as osp


class MultiLiveDataPanel(DefaultMultiLiveDataPanel):
    ui = f'{osp.dirname(__file__)}/ui_files/live.ui'

    def __init__(self, parent, client, options):
        DefaultMultiLiveDataPanel.__init__(self, parent, client, options)
        self.last_save_location = None
        self.setControlsEnabled(False)

    @pyqtSlot()
    def on_actionSaveData_triggered(self):
        self.export_data_to_file()

    def export_data_to_file(self):
        filename = QFileDialog.getSaveFileName(
            self,
            'Save table',
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

    def load_data_from_file(self):
        pass
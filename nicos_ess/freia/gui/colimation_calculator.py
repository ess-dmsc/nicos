from logging import WARNING

import numpy as np

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QIdentityProxyModel, Qt, QTableView
from nicos.utils import findResource

DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


class TableProxyModel(QIdentityProxyModel):
    def __init__(self, parent=None):
        super(TableProxyModel, self).__init__(parent)
        self._columns = set()

    def columnReadOnly(self, column):
        return column in self._columns

    def setColumnReadOnly(self, column, readonly=True):
        if readonly:
            self._columns.add(column)
        else:
            self._columns.discard(column)

    def flags(self, index):
        flags = super(TableProxyModel, self).flags(index)
        if self.columnReadOnly(index.column()):
            flags &= ~Qt.ItemIsEditable
        return flags


class ColimationPanel(Panel):
    panelName = "Freia Colimation Slit Calculator"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(
            self, findResource("nicos_ess/freia/gui/ui_files/freia_colimation_slit.ui")
        )

        self.setup_calc_table()

    def resolution_to_slit(self, l2, l12, ia, res, footprint):
        sinTheta = (footprint / 1000) * (np.sin(np.radians(ia)))
        slitDeltaTheta = np.radians(ia * res)

        slit2 = sinTheta - (2 * l2 * np.tan(slitDeltaTheta))
        slit1 = (2 * l12 * np.tan(slitDeltaTheta)) - slit2
        slit2 = float(slit2 * 1000)
        slit1 = float(slit1 * 1000)

        return slit1, slit2, sinTheta

    def slit_to_resoultion(self, l2, l12, ia, slit1, slit2):
        slit1 = slit1 / 1000
        slit2 = slit2 / 1000
        dist_ratio = l2 / l12
        beam_height = slit2 + (dist_ratio) * (slit1 + slit2)

        penumbra = float((beam_height / np.sin(np.deg2rad(ia))) * 1000)
        umbra = float((slit2 * 1000) / (np.sin(np.radians(ia))))

        slitDeltaTheta = (
            float(np.rad2deg(np.arctan((slit1 + slit2) / (2 * l12))) / ia) * 100
        )
        sinTheta = (
            float(
                DISTRIBUTION / (l12 * np.radians(ia)) * np.sqrt((slit1**2) + (slit2**2))
            )
            * 100
        )

        return penumbra, umbra, slitDeltaTheta, sinTheta, beam_height

    def on_run_pressed(self):
        pass

    def on_calcMode_currentTextChanged(self):
        pass

    def setup_calc_table(self):
        self.calcTable.resizeColumnToContents(0)
        self.calcTable.resizeColumnToContents(2)

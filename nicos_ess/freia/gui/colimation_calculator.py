from logging import WARNING

import numpy as np

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import pyqtSlot
from nicos.protocols.cache import cache_load
from nicos.utils import findResource

# https://www.sciencedirect.com/science/article/pii/S0921452604011792?pes=vor&utm_source=scopus&getft_integrator=scopus
# Distribution Full-Width Half-Maximum Delta with rectangular distribution at Full-Width
# Simplified from (2*np.sqrt(2*np.log(2))) * (1/(2*np.sqrt(3)))
DISTRIBUTION = np.sqrt((2 * np.log(2)) / 3)


class ColimationPanel(Panel):
    panelName = "Freia Colimation Slit Calculator"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(
            self, findResource("nicos_ess/freia/gui/ui_files/freia_colimation_slit.ui")
        )
        self.opmode = ""
        self.on_calcMode_currentTextChanged()  # refresh to update view

    def resolution_to_slit(self, l2, l12, ia, res, footprint):
        res_percent = res / 100
        footprint_m = footprint / 1000

        sinIa = np.sin(np.deg2rad(ia))
        fSinTheta = footprint_m * sinIa
        slitDeltaTheta = np.tan(np.radians(ia * res_percent))

        slit2_m = fSinTheta - (2 * l2 * slitDeltaTheta)
        slit1_m = (2 * l12 * slitDeltaTheta) - slit2_m

        slit1_mm = float(1000 * slit1_m)
        slit2_mm = float(1000 * slit2_m)

        return [slit1_mm, slit2_mm]

    def slit_to_resoultion(self, l2, l12, ia, slit1_mm, slit2_mm):
        slit1_m = slit1_mm / 1000
        slit2_m = slit2_mm / 1000
        dist_ratio = l2 / l12
        sinIa = np.sin(np.deg2rad(ia))

        beam_height = slit2_m + dist_ratio * (slit1_m + slit2_m)
        penumbra = float((beam_height / sinIa) * 1000)
        umbra = float((slit2_mm / sinIa))

        # return percentage for slitDeltaTheta and resolution
        slitDeltaTheta = float(
            (np.rad2deg(np.arctan((slit1_m + slit2_m) / (2 * l12))) / ia) * 100
        )
        res = (
            float(
                DISTRIBUTION
                / (l12 * np.radians(ia))
                * np.sqrt((slit1_m**2) + (slit2_m**2))
            )
            * 100
        )

        return [penumbra, umbra, slitDeltaTheta, res]

    def on_run_pressed(self):
        if self.opmode == "Resolution to Slit":
            l2 = self.l2sIn.value()
            l12 = self.l12In.value()
            theta = self.thetaIn.value()
            res = self.resIn.value()
            ft = self.ftIn.value()

            # self.showError(f"Values R2S: {value}")
            d1, d2 = self.resolution_to_slit(l2, l12, theta, res, ft)
            self.showError(f"{d1} | {d2}")
            self.d1Out.setValue(d1)
            self.d2Out.setValue(d2)

        elif self.opmode == "Slit to Resolution":
            input = [self.l2In, self.l12In, self.thetaIn, self.d1In, self.d2In]
            value = []
        else:
            self.showError("ERROR: No Opmode Found")

    def on_calcMode_currentTextChanged(self):
        self.opmode = self.calcMode.currentText()
        if self.opmode == "Resolution to Slit":
            self.d1In.setVisible(False)
            self.d2In.setVisible(False)

            self.resOut.setVisible(False)
            self.penumbra.setVisible(False)
            self.umbra.setVisible(False)
            self.beamH.setVisible(False)

            self.resIn.setVisible(True)
            self.ftIn.setVisible(True)

            self.d1Out.setVisible(True)
            self.d2Out.setVisible(True)

        elif self.opmode == "Slit to Resolution":
            self.d1In.setVisible(True)
            self.d2In.setVisible(True)

            self.resOut.setVisible(True)
            self.penumbra.setVisible(True)
            self.umbra.setVisible(True)
            self.beamH.setVisible(True)

            self.resIn.setVisible(False)
            self.ftIn.setVisible(False)

            self.d1Out.setVisible(False)
            self.d2Out.setVisible(False)
        else:
            self.showError("ERROR: No Opmode Found")

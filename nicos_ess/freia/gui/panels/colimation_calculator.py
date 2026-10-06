from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.utils import findResource
from nicos_ess.freia.devices import collimation_helpers as col


class CollimationPanel(Panel):
    panelName = "Freia Colimation Slit Calculator"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(
            self,
            findResource(
                "nicos_ess/freia/gui/panels/ui_files/freia_collimation_slit.ui"
            ),
        )
        self.opmode = ""
        self.on_calcMode_currentTextChanged()  # refresh to update view

    def on_run_pressed(self):
        if self.opmode == "Resolution to Slit":
            l2 = self.l2sIn.value()
            l12 = self.l12In.value()
            theta = self.thetaIn.value()
            res = self.resIn.value()
            ft = self.ftIn.value()

            d1, d2 = col.resolution_to_slit(l2, l12, theta, res, ft)
            self.d1Out.setValue(d1)
            self.d2Out.setValue(d2)

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

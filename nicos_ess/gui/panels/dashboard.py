from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.utils import findResource


class Dashboard(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/dashboard.ui"))

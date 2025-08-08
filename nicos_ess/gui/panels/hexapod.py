from logging import WARNING

from nicos.clients.gui.dialogs.error import ErrorDialog
from nicos.clients.gui.panels import Panel, showPanel
from nicos.clients.gui.utils import ScriptExecQuestion, dialogFromUi, loadUi
from nicos.core import ADMIN
from nicos.core.status import BUSY, DISABLED, ERROR, NOTREACHED, OK, UNKNOWN, WARN
from nicos.guisupport.colors import colors
from nicos.guisupport.qt import (
    pyqtSignal,
    pyqtSlot,
    sip,
)
from nicos.guisupport.typedvalue import ComboWidget, DeviceParamEdit, DeviceValueEdit
from nicos.protocols.cache import OP_TELL, cache_dump, cache_load
from nicos.utils import AttrDict, findResource
from nicos_ess.gui.panels.panel import Panel
from nicos_ess.gui.utils import get_icon


class HexapodInfo(AttrDict):
    def __init__():
        return


class HexapodPanel(Panel):
    """Provides a panel to view hexapod status. Currently a conceptual panel that
    will not properly connect to a hexapod. Emulates hexapod using virtual motors for each
    'direction' the hexapod should be able to move in with set limits per motor"""

    panelName = "Fake Hexapod Controls"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/hexapod_v3.ui"))

        self.client = client
        self.device_panel = parent
        self.options = options
        self.grpSpd.setVisible(False)  # To Add

    def on_butStart_pressed(self):
        # get data from spin boxes and add to the move command
        self._get_hexapod_info()

    def on_butStop_pressed(self):
        self.exec_command("stop(hexapod)")

    def exec_command(self, command):
        self.client.tell("exec", command)

    def _get_hexapod_info(self):
        """Successful test to obtain the attached device vars with the names provided in setup.
        Does not contain the parameters from hexapod, only attached devices
        Next: Combine parameter data from hexapod and the attached devices with their own parameter data into
        accessible dictionary data structure for manipulation"""

        # This needs to be cleaned up
        # Finds and sorts out the attached devices to the hexapod device
        test = self.client.eval("session.getSetupInfo()", {})
        self.hexapod_device = test["virtual_hexapod"]["devices"]["hexapod"][0]
        self._adevs = test["virtual_hexapod"]["devices"]["hexapod"][1]
        del self._adevs["description"]
        length = len(self._adevs)

        self.showError(f"{self.hexapod}")

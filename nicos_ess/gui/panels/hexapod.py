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
        # self.setup_connections(client)

    def setup_connections(self, client):
        # client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)
        client.setup.connect(self.on_client_setup)
        client.disconnected.connect(self.on_client_disconnect)

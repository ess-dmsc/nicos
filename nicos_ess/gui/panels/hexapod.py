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

    panelName = "Hexapod Controller"

    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/gui/panels/ui_files/hexapod_v3.ui"))

        # Note: testing with 'freia_hexapod' which is a currently hardcoded name
        self.setup_connections(client)
        self.devname = ""
        self.adevs = {}

    def on_butStart_pressed(self):
        # currently used to check collected info on hexapod
        self._get_hexapod_info()
        self._move()
        # self.showError(f"{self.devname}")

    def on_butStop_pressed(self):
        self.exec_command("stop(freia_hexapod)")

    def _move(self):
        # collect positions from spinboxes and run move command (needs to be cleaned up)
        # does not pop up error panel
        target = [
            self.newTx.value(),
            self.newTy.value(),
            self.newTz.value(),
            self.newRx.value(),
            self.newRy.value(),
            self.newRz.value(),
        ]
        self.exec_command(f"move(freia_hexapod, ({target}))")

    def exec_command(self, command):
        self.client.tell("exec", command)

    def setup_connections(self, client):
        client.cache.connect(self.on_client_cache)
        client.connected.connect(self.on_client_connected)
        client.setup.connect(self.on_client_setup)
        client.disconnected.connect(self.on_client_disconnected)

    def on_client_cache(self):
        return

    def on_client_connected(self):
        if self.devname == "":
            self._get_hexapod_name(self.devname)
        self._get_attached_devices(self.adevs)
        self._show_controls()

    def on_client_setup(self):
        if self.devname == "":
            self._get_hexapod_name(self.devname)
        self._get_attached_devices(self.adevs)
        self._show_controls()

    def on_client_disconnected(self):
        self.devname == ""
        self._show_controls()

    # should show controls if hexapod is within selected devices. Otherwise nothing
    def _show_controls(self):
        devices = self.client.eval("session.devices", {})
        for devname in devices:
            if "hexapod" in devices[devname].lower():
                self.curPos.show()
                self.grpStatus.show()
                self.newPos.show()

                # to add later
                self.grpSpd.hide()
                self.presets.hide()
                return
            else:
                continue
        self.curPos.hide()
        self.grpStatus.hide()
        self.newPos.hide()

        # to add later
        self.grpSpd.hide()
        self.presets.hide()
        return

    def _get_hexapod_name(self, devname):
        if devname != "":
            return devname
        else:
            name = self.client.getDeviceList(
                needs_class="nicos_ess.devices.virtual.hexapod.VirtualHexapod"
            )
        self.devname = name[0]  # we want the content of the list not the list itself

    def _get_attached_devices(self, adevs):
        return

    def _get_hexapod_info(self):
        """Successful test to obtain the attached device vars with the names provided in setup.
        Does not contain the parameters from hexapod, only attached devices
        Next: Combine parameter data from hexapod and the attached devices with their own parameter data into
        accessible dictionary data structure for manipulation"""

        # This needs to be cleaned up
        # Finds and sorts out the attached devices to the hexapod device
        setup = self.client.eval("session.getSetupInfo()", {})
        self.hexapod_device = setup["virtual_hexapod"]["devices"][f"{self.devname}"][
            0
        ]  # freia_hexapod to change to devname
        self.adevs = setup["virtual_hexapod"]["devices"][f"{self.devname}"][1]
        del self.adevs["description"]
        length = len(self.adevs)  # how many devices

        self.showError(
            f"devices: {self.adevs} \n length:{length}"
        )  # {attach_dev name : setup_dev name}

        # self.devs{}
        # currently pulls WAY too much stuff. Thin it out!
        # for key in self.adevs:
        #    device = self.client.getDeviceParams(self.adevs[key])
        #    for param in ['curvalue', 'unit']:

        # value = device[param]
        # self.devs.update({f"{key}": {f"{param}": value}} )
        # self.devs.update({f"{key}": self.client.getDeviceParams(self._adevs[key])})
        # self.devs.update({f"{'tx'}": self.client.getDeviceParams(self._adevs['tx'])})

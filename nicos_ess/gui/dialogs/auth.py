"""Dialog for entering authentication data."""

import getpass
from collections import OrderedDict

from nicos.clients.base import ConnectionData
from nicos.clients.gui.utils import loadUi
from nicos.guisupport.qt import QDialog, QPixmap, QSize
from nicos.protocols.daemon.classic import DEFAULT_PORT
from nicos.utils import findResource


class ConnectionDialog(QDialog):
    """A dialog to request connection parameters."""

    @classmethod
    def getConnectionData(
        cls, parent, connpresets, default_server=None, default_user=None
    ):
        self = cls(parent, connpresets, default_server, default_user)
        ret = self.exec()
        if ret != QDialog.DialogCode.Accepted:
            return None, None, None, ""
        new_addr = self.txtServer.text()
        try:
            host, port = new_addr.split(":")
            port = int(port)
        except ValueError:
            host = new_addr
            port = DEFAULT_PORT
        new_data = ConnectionData(
            host, port, self.userName.text(), self.txtPassword.text()
        )
        new_data.viewonly = self.viewonly.isChecked()
        new_data.expertmode = self.expertmode.isChecked()
        return None, new_data, None, ""

    def __init__(self, parent, connpresets, default_server, default_user):
        QDialog.__init__(self, parent)
        loadUi(self, findResource("nicos_ess/gui/dialogs/auth.ui"))
        if hasattr(parent, "facility_logo") and parent.facility_logo:
            self.logoLabel.setPixmap(QPixmap(parent.facility_logo))
        self.connpresets = OrderedDict(sorted(connpresets.items()))

        self._populate_where_possible(default_server, default_user)

        self.resize(QSize(self.width(), self.minimumSize().height()))

    def _populate_where_possible(self, server, user):
        user = user if user else self._get_local_user()
        self.userName.setText(user)
        self.txtServer.setText(server)

    def _get_local_user(self):
        return getpass.getuser()

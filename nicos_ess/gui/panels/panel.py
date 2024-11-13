from nicos.clients.gui.panels import Panel


class PanelBase(Panel):
    def __init__(self, parent, client, options):
        Panel.__init__(self, parent, client, options)

    def initialise_connection_status_listeners(self):
        if self.client.isconnected:
            self.on_client_connected()
        else:
            self.on_client_disconnected()
        self.client.connected.connect(self.on_client_connected)
        self.client.disconnected.connect(self.on_client_disconnected)

    def on_client_connected(self):
        self.setViewOnly(self.client.viewonly)

    def on_client_disconnected(self):
        self.setViewOnly(True)

import pyads

from nicos.core import Attach, HasCommunication, Override, Param, Readable, status
from nicos.core.errors import CommunicationError
from nicos.core.params import ipv4


class ADSServer(HasCommunication, Readable):
    """Handle communication to the MCU w/o EPICS"""

    parameters = {
        "ip": Param(
            "IP address of Beckhoff terminal", type=ipv4, preinit=True, mandatory=True
        ),
        "amsnetid": Param(
            "ID of Beckhoff terminal", type=str, preinit=True, mandatory=True
        ),
        "port": Param(
            "ADS port of PLC terminal", type=int, preinit=True, mandatory=True
        ),
        "timeout": Param(
            "Communication timeout for pyads",
            type=float,
            prefercache=False,
            preinit=True,
            default=5.0,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, userparam=False, settable=False)
    }

    def doPreinit(self, mode):
        self._statusok = True

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        if not self._statusok:
            return status.WARN, "no communication"
        return status.OK, ""

    def communicate(self, attribute, ads_type):
        return self._com_retry("ADS call", self._call, attribute, ads_type)

    def _call(self, attribute, ads_type):
        # open ADS connection and close after communication
        with pyads.Connection(
            self.amsnetid, self.port, ip_address=self.ip
        ) as connection:
            connection.set_timeout(int(self.timeout * 1000))
            return connection.read_by_name(attribute, ads_type)

    def _com_return(self, result, info):
        """Overwrite to set status to OK"""
        self._statusok = True
        return result

    def _com_raise(self, err, info):
        """Overwrite to set status to not OK."""
        self._statusok = False
        raise CommunicationError(self, str(err))


class PT100(Readable):
    """PT100 temperature sensor device"""

    parameters = {
        "attribute": Param(
            "Index of the axis to be read",
            type=str,
            default="nTempM1",
        ),
    }

    parameter_overrides = {
        "unit": Override(default="C", mandatory=False, settable=False, userparam=False),
    }

    attached_devices = {"server": Attach("Server for communication", ADSServer)}

    valuetype = float

    def doRead(self, maxage=0):
        return (
            self._attached_server.communicate(
                "main." + self.attribute, pyads.PLCTYPE_INT
            )
            * 0.1
        )

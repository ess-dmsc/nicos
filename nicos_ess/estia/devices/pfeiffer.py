"""
This module contains a device for reading the Pfeiffer TPG 261
vacuum gauge controller using a Moxa terminal server.
"""

from nicos.core import Override, Readable, status
from nicos.devices.vendor.moxa import MoxaCommunicator


class PfeifferTPG261(MoxaCommunicator, Readable):
    """Device for reading the Pfeiffer TPG 261 vacuum gauge controller using
    a Moxa terminal server.
    """

    parameter_overrides = {
        "unit": Override(
            default="mbar", mandatory=False, settable=False, userparam=False
        ),
    }

    valuetype = float

    _error_codes = {
        "0000": (status.OK, ""),
        "1000": (status.ERROR, "Controller error"),
        "0100": (status.WARN, "No sensor connected"),
        "0010": (status.ERROR, "Inadmissible parameter"),
        "0001": (status.ERROR, "Syntax Error"),
    }

    def _command_post_send(self, sock):
        reply = sock.recv(3)
        if reply != "\x06\r\n":
            self._flush_tty(sock)
            raise OSError("No ACK reply.")
        # send ENQ signal
        sock.send("\x05\r\n")

    def _read_pressure(self):
        res = self._command_tty("PRX")
        value = res.split(",")[1]
        return float(value)

    def doRead(self, maxage=0):
        return self._com_retry("COM get gauge value", self._read_pressure)

    def doStatus(self, maxage=0):
        res = self._com_retry('COM send "ERR"', self._command_tty, "ERR")
        if res is None:
            return status.WARN, "no communication"
        try:
            return self._error_codes[res.strip()]
        except KeyError:
            self._com_retry(
                "Flush COM port in case of communication issues", self._flush_tty
            )
            return status.WARN, "communication error"

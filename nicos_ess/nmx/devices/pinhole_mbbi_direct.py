from dataclasses import replace

from nicos.core import Param, status
from nicos_ess.devices.epics.mbbi_direct import MBBIDirectStatus


class PinholeStatus(MBBIDirectStatus):
    """
    Handles the NMX pinhole status (which is an EPICS MBBI direct record).
    TODO: Some of the changes here can be moved later to the parent class.
    """

    parameters = {
        "bitvalue_prefix": Param(
            "Prefix for bit values",
            type=str,
            settable=False,
            mandatory=False,
            default="",
        ),
    }

    def _build_epics_channels(self):
        channels = super()._build_epics_channels()
        for i in range(self.number_of_bits):
            hex_digit = f"{i:x}".upper()
            name = f"bit_value_{i}"
            channels[name] = replace(
                channels[name], pv_suffix=f"{self.bitvalue_prefix}.B{hex_digit}"
            )
        return channels

    def _compute_status(self, maxage=0):
        in_alarm = []
        for i in range(self.number_of_bits):
            value = self._read_channel_cached(f"bit_value_{i}", maxage=maxage)
            if value == 0:
                continue

            message = self._read_channel_cached(f"bit_name_{i}", maxage=maxage)
            in_alarm.append(message)
        return status.OK, ", ".join(in_alarm)

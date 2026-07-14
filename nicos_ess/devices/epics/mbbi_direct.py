from nicos.core import (
    Override,
    Param,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsStatusOnlyReadable,
    readback_channel,
    status_channel,
)


class MBBIDirectStatus(EpicsStatusOnlyReadable):
    """
    This device automatically handles EPICS MBBI direct records with named bits.
    """

    parameters = {
        "pv_root": Param(
            "PV root for device", type=str, mandatory=True, userparam=False
        ),
        "number_of_bits": Param(
            "Number of bits to monitor",
            type=int,
            settable=False,
            mandatory=True,
        ),
        "bitname_prefix": Param(
            "Prefix for bit names",
            type=str,
            settable=False,
            mandatory=False,
            default="BitNam",
        ),
    }
    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "communication"
    _connect_channels = ("communication",)

    def _build_epics_channels(self):
        channels = {
            "communication": status_channel(""),
        }
        for i in range(self.number_of_bits):
            hex_digit = f"{i:x}".upper()
            channels[f"bit_value_{i}"] = readback_channel(
                f".B{hex_digit}", refresh_status=True
            )
            channels[f"bit_name_{i}"] = readback_channel(
                f"{self.bitname_prefix}{i}",
                as_string=True,
                refresh_status=True,
            )
        return channels

    def _compute_status(self, maxage=0):
        in_alarm = []
        highest_severity = status.OK
        for i in range(self.number_of_bits):
            value = self._read_channel_cached(f"bit_value_{i}", maxage=maxage)
            if value == 0:
                continue

            message = self._read_channel_cached(f"bit_name_{i}", maxage=maxage)
            highest_severity = status.WARN
            self._log_alarm_once(f"bit_value_{i}", status.WARN, message)
            in_alarm.append(f"{message} Alarm")
        return highest_severity, ", ".join(in_alarm)

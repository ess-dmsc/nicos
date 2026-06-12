from nicos.core import (
    Override,
    Param,
    Readable,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelInfo,
    EpicsChannelRole,
    EpicsDeviceBase,
)


class MBBIDirectStatus(EpicsDeviceBase, Readable):
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

    _default_pv_root_attr = "pv_root"
    _primary_channel = "communication"

    def _build_epics_channels(self):
        channels = {
            "communication": EpicsChannelInfo("", "", EpicsChannelRole.STATUS),
        }
        for i in range(self.number_of_bits):
            hex_digit = f"{i:x}".upper()
            channels[f"bit_value_{i}"] = EpicsChannelInfo(
                "", f".B{hex_digit}", EpicsChannelRole.VALUE_AND_STATUS
            )
            channels[f"bit_name_{i}"] = EpicsChannelInfo(
                "",
                f"{self.bitname_prefix}{i}",
                EpicsChannelRole.VALUE_AND_STATUS,
                as_string=True,
            )
        return channels

    def doPreinit(self, mode):
        self._alarm_state = {}
        EpicsDeviceBase.doPreinit(self, mode)

    def _pvs_to_connect(self):
        # Checking one PV is enough to see that the IOC is there.
        return [self._epics.pv_name_for("communication")]

    def doRead(self, maxage=0):
        return ""

    def _compute_status(self, maxage=0):
        in_alarm = []
        highest_severity = status.OK
        for i in range(self.number_of_bits):
            value = self._read_channel_cached(f"bit_value_{i}", maxage=maxage)
            if value == 0:
                continue

            message = self._read_channel_cached(f"bit_name_{i}", maxage=maxage)
            highest_severity = severity = status.WARN

            if self._alarm_state.get(f"bit_value_{i}") != (severity, message):
                self._write_alarm_to_log(f"bit_value_{i}", severity, message)
            in_alarm.append(f"{message} Alarm")
            self._alarm_state[f"bit_value_{i}"] = (severity, message)
        return highest_severity, ", ".join(in_alarm)

    def _write_alarm_to_log(self, name, severity, message):
        if severity in [status.ERROR, status.UNKNOWN]:
            self.log.error("%s (%s)", name, message)
        elif severity == status.WARN:
            self.log.warning("%s (%s)", name, message)

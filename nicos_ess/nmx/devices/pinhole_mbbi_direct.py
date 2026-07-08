from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Attach,
    Override,
    Param,
    Readable,
    Waitable,
    listof,
    status,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)
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

    def doPreinit(self, mode):
        self._bit_map = {}
        self._alarm_state = {}
        self._record_fields = {}
        self._record_fields["communication"] = RecordInfo(
            "value",
            "",
            RecordType.STATUS,
        )
        for i in range(self.number_of_bits):
            hex = f"{i:x}".upper()
            self._record_fields[f"bit_value_{i}"] = RecordInfo(
                "",
                f"{self.bitvalue_prefix}.B{hex}",
                RecordType.VALUE,  # Configurable bit value
            )
            self._record_fields[f"bit_name_{i}"] = RecordInfo(
                "", f"{self.bitname_prefix}{i}", RecordType.VALUE
            )
            self._bit_map[f"bit_value_{i}"] = f"bit_name_{i}"

        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        if mode != SIMULATION:
            # Check one of the PVs exists
            self._epics_wrapper.connect_pv(self.pv_root)

    def _do_status(self):
        in_alarm = []
        highest_severity = status.OK
        for name in self._record_fields:
            if name not in self._bit_map.keys():
                continue

            value = self._get_cached_value_or_ask(name)
            if value == 0:
                continue

            bit_name = self._bit_map.get(name, None)
            message = self._get_cached_value_or_ask(bit_name)
            # highest_severity = severity = status.WARN
            severity = highest_severity

            # if self._alarm_state.get(name) != (severity, message):
            #    self._write_alarm_to_log(name, severity, message)
            in_alarm.append(f"{message}")  # Removing "alarm" word
            self._alarm_state[name] = (severity, message)
        return highest_severity, ", ".join(in_alarm)

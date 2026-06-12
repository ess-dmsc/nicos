from nicos.core import (
    SIMULATION,
    Param,
    none_or,
    pvname,
    status,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva.epics_common import (
    PvReadOrWrite,
    RecordInfo,
    RecordType,
    _update_mapped_choices,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsMappedMoveable,
    EpicsMappedReadable,
)


class EpicsShutter(EpicsMappedMoveable):
    """
    May become a general class. Works same as EpicsMappedMoveable, but uses
    choices from the writepv instead of readpv for the mapping.
    """

    _publish_read_choices = False

    parameters = {
        "resetpv": Param(
            "PV for resetting device",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
        "msgtxt": Param(
            "PV of the message text",
            type=pvname,
            mandatory=False,
            userparam=False,
        ),
    }

    def _after_subscribe(self, mode):
        # Hardware quirk: the readpv and writepv expose different enums
        # (read includes transient states like Opening/Closing). Keep separate
        # internal maps and publish the write map as the accepted target set.
        if mode != SIMULATION:
            _update_mapped_choices(self, PvReadOrWrite.readpv, publish=False)
            _update_mapped_choices(self, PvReadOrWrite.writepv)
        MappedMoveable.doInit(self, mode)

    def _read_msgtxt(self):
        return self._epics.get_pv_value(self.msgtxt, as_string=True)

    def _is_moving(self, maxage=0):
        return self._read_mapped_choice(maxage=maxage) in ("Closing", "Opening")

    def _compute_status(self, maxage=0):
        severity, msg = self._read_primary_alarm(maxage=maxage)
        if severity in [status.ERROR, status.WARN]:
            return severity, self._read_msgtxt()
        if self._is_moving(maxage=maxage):
            return status.BUSY, self._read_msgtxt()
        return severity, self._read_msgtxt()


class EpicsHeavyShutter(EpicsMappedReadable):
    """
    Readable class for heavy shutters with optional reset capabilities
    """

    parameters = {
        "resetpv": Param(
            "PV for resetting device",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
    }

    def _build_record_fields(self):
        record_fields = {
            "readpv": RecordInfo("value", "", RecordType.BOTH, as_string=True),
        }
        if self.resetpv:
            record_fields["resetpv"] = RecordInfo("", "", RecordType.VALUE)
        return record_fields

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._epics.put_pv("resetpv", True)
        else:
            self.log.warning(
                "Reset isn't available on device or the resetpv is missing"
            )

from nicos.core import (
    Param,
    none_or,
    pvname,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelInfo,
    EpicsChannelRole,
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

    _mapping_channel = "write"

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

    def _read_msgtxt(self):
        return self._epics.get_pv_value(self.msgtxt, as_string=True)

    def _is_moving(self, maxage=0):
        return self.read(maxage) in ("Closing", "Opening")

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

    def _build_epics_channels(self):
        epics_channels = {
            "read": EpicsChannelInfo(
                "value",
                "",
                EpicsChannelRole.VALUE_AND_STATUS,
                as_string=True,
                pv_attr="readpv",
            ),
        }
        if self.resetpv:
            epics_channels["reset"] = EpicsChannelInfo(
                "", "", EpicsChannelRole.VALUE, pv_attr="resetpv"
            )
        return epics_channels

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._epics.put_channel_value("reset", True)
        else:
            self.log.warning(
                "Reset isn't available on device or the resetpv is missing"
            )

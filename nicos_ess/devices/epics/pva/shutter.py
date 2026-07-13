from nicos.core import (
    Param,
    none_or,
    pvname,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    command_channel,
    readback_channel,
    status_channel,
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
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
    }

    def _build_epics_channels(self):
        epics_channels = super()._build_epics_channels()
        # Named 'message' so the cache key does not collide with the
        # 'msgtxt' parameter (which holds the PV name).
        epics_channels["message"] = status_channel(
            "",
            as_string=True,
            pv_name_attr="msgtxt",
            allow_missing_pv=True,
            affects_status=False,
        )
        return epics_channels

    def _read_msgtxt(self, maxage=None):
        if not self.msgtxt:
            return ""
        return self._read_channel_cached("message", maxage=maxage)

    def _is_moving(self, maxage=0):
        return self.read(maxage) in ("Closing", "Opening")

    def _compute_status(self, maxage=0):
        severity, _ = self._read_primary_alarm(maxage=maxage)
        if severity in [status.ERROR, status.WARN]:
            return severity, self._read_msgtxt(maxage=maxage)
        if self._is_moving(maxage=maxage):
            return status.BUSY, self._read_msgtxt(maxage=maxage)
        return severity, self._read_msgtxt(maxage=maxage)


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
            "read": readback_channel(
                "",
                cache_key="value",
                primary=True,
                as_string=True,
                pv_name_attr="readpv",
            ),
        }
        if self.resetpv:
            epics_channels["reset"] = command_channel("", pv_name_attr="resetpv")
        return epics_channels

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._epics.put_channel_value("reset", True)
        else:
            self.log.warning(
                "Reset isn't available on device or the resetpv is missing"
            )

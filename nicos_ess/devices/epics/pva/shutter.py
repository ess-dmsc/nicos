from nicos.core import (
    Param,
    none_or,
    pvname,
    status,
)
from nicos_ess.devices.epics.pva.epics_common import (
    command_channel,
    enum_status_channel,
    status_channel,
    worst_status,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsMappedMoveable,
    EpicsMappedReadable,
)


class EpicsShutter(EpicsMappedMoveable):
    """
    Pneumatic actuator whose command choices and state labels are independent.

    Mapping choices come from ``writepv``.  The standardized actuator
    ``statuspv`` lifecycle controls completion; the PLC-defined ``readpv``
    labels remain presentation only.
    """

    _mapping_channel = "write"

    _STATUS_MAP = {
        "IDLE": status.OK,
        "DISABLED": status.DISABLED,
        "WARN": status.WARN,
        "RESET": status.BUSY,
        "START": status.BUSY,
        "BUSY": status.BUSY,
        "STOP": status.BUSY,
    }

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
            mandatory=True,
            userparam=False,
        ),
        "statuspv": Param(
            "PV of the actuator StatusCode lifecycle enum",
            type=pvname,
            mandatory=True,
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
        )
        epics_channels["status_code"] = enum_status_channel(
            "",
            cache_key="status_code",
            pv_name_attr="statuspv",
        )
        return epics_channels

    def _read_msgtxt(self, maxage=None):
        return self._read_channel_cached("message", maxage=maxage)

    @staticmethod
    def _normalize_status_code(value):
        return str(value).strip().upper()

    def _read_status_code(self, maxage=0):
        return self._normalize_status_code(
            self._read_channel_cached("status_code", maxage=maxage)
        )

    def doStart(self, target):
        super().doStart(target)
        # The ADS write returns before the next IOC readback cycle.  Wait only
        # for the short hardware acknowledgement, not for the movement.  This
        # prevents the previous IDLE from completing the new NICOS target.
        self._epics.wait_for(
            "status_code",
            lambda value: self._normalize_status_code(value) != "IDLE",
            timeout=self.epicstimeout,
        )

    def _compute_status(self, maxage=0):
        severity, _ = self._read_primary_alarm(maxage=maxage)
        message = self._read_msgtxt(maxage=maxage)
        code = self._read_status_code(maxage=maxage)
        code_status = self._STATUS_MAP.get(code, status.ERROR)
        code_message = message
        if not code_message and code_status == status.BUSY:
            code_message = (
                f"moving to {self.target}" if self.target is not None else "moving"
            )
        elif not code_message and code_status != status.OK:
            code_message = code
        return worst_status((severity, message), (code_status, code_message))

    def doFinish(self):
        # Command and AuxBits07 labels are independent PLC configuration.
        # StatusCode is the only generic completion/error contract.
        return False


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
        epics_channels = dict(super()._build_epics_channels())
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

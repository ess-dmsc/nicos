import time

from nicos import session
from nicos.core import (
    POLLER,
    Param,
    none_or,
    pvname,
    status,
)
from nicos.devices.abstract import MappedMoveable
from nicos.devices.epics.pva import EpicsMappedReadable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsMappedMoveable,
    _update_mapped_choices,
    get_from_cache_or,
    pvReadOrWrite,
)


class EpicsShutter(EpicsMappedMoveable):
    """
    May become a general class. Works same as EpicsMappedMoveable, but uses
    choices from the writepv instead of readpv for the mapping.
    """

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

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            _update_mapped_choices(self, pvReadOrWrite.readpv)

            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    self._record_fields["readpv"].cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    self._record_fields["writepv"].cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            if self.targetpv:
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self.targetpv,
                        self._record_fields["targetpv"].cache_key,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

        if session.sessiontype != POLLER:
            _update_mapped_choices(self, pvReadOrWrite.writepv)
        MappedMoveable.doInit(self, mode)

    def _read_msgtxt(self):
        return self._epics_wrapper.get_pv_value(self.msgtxt, as_string=True)

    def _is_moving(self):
        choices = self._epics_wrapper.get_value_choices(self.readpv)
        choice_mapping = {choice: i for i, choice in enumerate(choices)}
        if choice_mapping[self.doRead()] in (1, 2):
            return True

    def _do_status(self):
        try:
            severity, msg = self._epics_wrapper.get_alarm_status(self.readpv)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if severity in [status.ERROR, status.WARN]:
            return severity, self._read_msgtxt()
        if self._is_moving():
            return status.BUSY, self._read_msgtxt()
        return severity, self._read_msgtxt()

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name != self.readpv:
            # Unexpected updates ignored
            return
        self._cache.put(self._name, "status", self._do_status(), time.time())


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

    def _get_pv_parameters(self):
        return {"readpv"} | {"resetpv"} if self.resetpv else {"readpv"}

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._put_pv("resetpv", True)
        else:
            self.log.warn("Reset isn't available on device or the resetpv is missing")

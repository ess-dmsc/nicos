import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Param,
    none_or,
    pvname,
    status,
)
from nicos.devices.abstract import MappedMoveable
from nicos.devices.epics.pva import (
    EpicsDevice,
    EpicsMappedReadable,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsMappedMoveable,
    get_from_cache_or,
)


def _update_mapped_choices_from_writepv(mapped_device):
    choices = mapped_device._epics_wrapper.get_value_choices(mapped_device.writepv)
    new_mapping = {}
    for i, choice in enumerate(choices):
        new_mapping[choice] = i
    mapped_device._setROParam("mapping", new_mapping)
    mapped_device._inverse_mapping = {}
    for k, v in mapped_device.mapping.items():
        mapped_device._inverse_mapping[v] = k


class EpicsShutter(EpicsMappedMoveable):
    """
    May become a general class. Works same as EpicsMappedMoveable, but uses
    choices from the writepv instead of readpv for the mapping.
    """

    parameters = {
        "openingbit": Param(
            "PV for the opening bit",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
        "closingbit": Param(
            "PV for the closing bit",
            type=none_or(pvname),
            mandatory=False,
            userparam=False,
        ),
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

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
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

        if session.sessiontype != POLLER and not self.monitor:
            _update_mapped_choices_from_writepv(self)
        MappedMoveable.doInit(self, mode)

    def doReadClosingbit(self, maxage=0):
        return get_from_cache_or(
            self,
            "value",
            lambda: self._epics_wrapper.get_pv_value(self.closingbit, as_string=False),
        )

    def doReadOpeningbit(self, maxage=0):
        return get_from_cache_or(
            self,
            "value",
            lambda: self._epics_wrapper.get_pv_value(self.openingbit, as_string=False),
        )

    def doReadMsgTxt(self, maxage=0):
        return get_from_cache_or(
            self,
            "status",
            lambda: self._epics_wrapper.get_pv_value(self.msgtxt, as_string=True),
        )

    def doIsMoving(self):
        if self.doReadClosingbit() or self.doReadOpeningbit():
            return True

    def _do_status(self):
        try:
            severity, msg = self._epics_wrapper.get_alarm_status(self.readpv)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if self.doIsMoving():
            return status.BUSY, self.doReadMsgTxt()
        return severity, msg

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name not in {self.readpv, self.writepv, self.targetpv}:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        if name == self.readpv:
            if not self.mapping:
                _update_mapped_choices_from_writepv(self)
            self._cache.put(
                self._name,
                param,
                self._inverse_mapping.get(value, value),
                time_stamp,
            )
            self._cache.put(self._name, "unit", units, time_stamp)
        if name == self.writepv and not self.target:
            self._cache.put(self._name, param, value, time_stamp)
        if name == self.targetpv:
            self._cache.put(self._name, param, value, time_stamp)

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

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
    EpicsMappedMoveable,
    EpicsMappedReadable,
)


def get_from_cache_or(device, cache_key, func):
    if device.monitor:
        result = device._cache.get(device._name, cache_key)
        if result is not None:
            return result
    return func()


def _update_mapped_choices(mapped_device):
    choices = mapped_device._epics_wrapper.get_value_choices(mapped_device.readpv)
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

    def _get_pv_parameters(self):
        pv_parameters = super()._get_pv_parameters()
        return pv_parameters | {"resetpv"} if self.resetpv else pv_parameters

    def doInit(self, mode):
        if mode == SIMULATION:
            return

        if session.sessiontype == POLLER and self.monitor:
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    "value",
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.readpv,
                    "value",
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    self.writepv,
                    "target",
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )

        EpicsDevice.doInit(self, mode)

        if session.sessiontype != POLLER:
            choices = self._epics_wrapper.get_value_choices(
                self._get_pv_name("writepv")
            )
            # Create mapping from EPICS information
            new_mapping = {}
            for i, choice in enumerate(choices):
                new_mapping[choice] = i
            self._setROParam("mapping", new_mapping)
        MappedMoveable.doInit(self, mode)

    def doReset(self):
        """Reset shutter state by writing on the configured 'resetpv' parameter"""

        if self.resetpv:
            self._put_pv("resetpv", True)
        else:
            self.log.warn("Reset isn't available on device or the resetpv is missing")

    def doStatus(self, maxage=0):
        try:
            severity, msg = self._epics_wrapper.get_alarm_status(self.readpv)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if severity in (status.ERROR, status.WARN):
            return severity, msg
        if self.doReadClosingbit() == 1 or self.doReadOpeningbit() == 1:
            return status.BUSY, self.doReadMsgTxt()
        return status.OK, ""

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if name not in {self.readpv, self.writepv, self.targetpv}:
            # Unexpected updates ignored
            return
        time_stamp = time.time()
        if name == self.readpv:
            if not self.mapping:
                _update_mapped_choices(self)
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
        self._cache.put(self._name, "status", (severity, message), time.time())

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != "value":
            return

        if is_connected:
            self.log.debug("%s connected!", name)
        else:
            self.log.warning("%s disconnected!", name)
            self._cache.put(
                self._name,
                "status",
                (status.ERROR, "communication failure"),
                time.time(),
            )


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

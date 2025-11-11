import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Attach,
    InvalidValueError,
    Override,
    Param,
    oneof,
    pvname,
    status,
    usermethod,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva import EpicsStringReadable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class SyringePumpController(EpicsParameters, MappedMoveable):
    """
    A device for controlling the NE1002 and NE1600 syringe pumps.

    This refactor keeps the same external behaviour (parameters, commands,
    validation logic, doRead/doStatus semantics), but switches to
    EpicsParameters to unify EPICS access and caching. The device:
      - exposes the mapped commands: start / stop / purge / pause / resume
      - reads the current textual *state* from the attached `status` device
      - reads error text from `message_pv` (non-empty => ERROR)
      - writes to start/stop/purge/pause PVs as before
    """

    parameters = {
        "start_pv": Param(
            "PV for starting the device", type=pvname, mandatory=True, userparam=False
        ),
        "stop_pv": Param(
            "PV for stopping the device", type=pvname, mandatory=True, userparam=False
        ),
        "purge_pv": Param(
            "PV for purging the device", type=pvname, mandatory=True, userparam=False
        ),
        "pause_pv": Param(
            "PV for pausing and resuming the device",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
        "message_pv": Param(
            "PV for reading error messages from the device",
            type=pvname,
            mandatory=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, userparam=False),
        "mapping": Override(
            mandatory=False, settable=False, userparam=False, volatile=True
        ),
    }

    attached_devices = {
        "status": Attach("Status of device", EpicsStringReadable),
    }

    def doPreinit(self, mode):
        # Logical keys for our PVs
        self._record_fields = {
            # cache_key, (pv is resolved via _pv() below)
            "message": RecordInfo("message", "message", RecordType.VALUE),
            "start": RecordInfo("start", "start", RecordType.VALUE),
            "stop": RecordInfo("stop", "stop", RecordType.VALUE),
            "purge": RecordInfo("purge", "purge", RecordType.VALUE),
            "pause": RecordInfo("pause", "pause", RecordType.VALUE),
        }

        self._key_to_param = {
            "message": "message_pv",
            "start": "start_pv",
            "stop": "stop_pv",
            "purge": "purge_pv",
            "pause": "pause_pv",
        }

        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)

        # Command mapping for MappedMoveable
        self._commands = {
            "start": self.start_pump,
            "stop": self.stop_pump,
            "purge": self.purge,
            "pause": self.pause_pump,
            "resume": self.resume_pump,
        }

        # Establish connection to message PV early so we get connection-status logs
        self._epics_wrapper.connect_pv(self._pv("message"))

    def doInit(self, mode):
        # Expose mapping on init (volatile, RO)
        self._setROParam(
            "mapping", {cmd: i for i, cmd in enumerate(self._commands.keys())}
        )

        # Subscribe to message PV updates for cache + status recomputation
        if session.sessiontype == POLLER and self.monitor:
            info = self._record_fields["message"]
            full_pv = self._pv("message")
            # value updates
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    full_pv,
                    info.cache_key,
                    self._value_change_callback,
                    self._connection_change_callback,
                )
            )
            # status/alarm updates
            self._epics_subscriptions.append(
                self._epics_wrapper.subscribe(
                    full_pv,
                    info.cache_key,
                    self._status_change_callback,
                    self._connection_change_callback,
                )
            )

        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands.keys())

    def _pv(self, key: str) -> str:
        param_name = self._key_to_param[key]
        return getattr(self, param_name)

    def _get_cached_pv_or_ask(self, key: str, as_string: bool = False):
        return get_from_cache_or(
            self,
            self._record_fields[key].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self._pv(key), as_string),
        )

    def _get_pv(self, key: str, as_string: bool = False):
        return self._epics_wrapper.get_pv_value(self._pv(key), as_string)

    def _put_pv(self, key: str, value):
        self._epics_wrapper.put_pv_value(self._pv(key), value)

    def _update_status(self, new_status, message):
        self._cache.put(self._name, "status", (new_status, message), time.time())

    def doStart(self, target):
        if target in self._commands:
            self._commands[target]()

    def doStop(self):
        self.stop_pump()

    def doRead(self, maxage=0):
        return self._attached_status.read(maxage)

    def doReadMapping(self):
        return {cmd: i for i, cmd in enumerate(self._commands.keys())}

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        if self._mode == SIMULATION:
            return status.OK, ""

        # Non-empty error message => ERROR with message
        try:
            device_msg = self._get_cached_pv_or_ask("message", as_string=True) or ""
        except Exception:
            # If we can't read the message PV, signal comms issue
            return status.ERROR, "communication failure (reading message PV)"

        if device_msg.strip():
            return status.ERROR, device_msg

        try:
            return self._attached_status.status(0)
        except Exception:
            return status.ERROR, "communication failure (reading status device)"

    @usermethod
    def start_pump(self):
        """Start pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state != "Stopped":
            raise InvalidValueError(
                "Cannot start from the current state, please stop the pump first"
            )
        self._put_pv("start", 1)

    @usermethod
    def stop_pump(self):
        """Stop pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state == "Stopped":
            self.log.warning("Stop request ignored as pump already stopped")
            return
        self._put_pv("stop", 2)

    @usermethod
    def purge(self):
        """Purge the pump"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state != "Stopped":
            raise InvalidValueError(
                "Cannot purge from the current state, please stop the pump first"
            )
        self._put_pv("purge", 3)

    @usermethod
    def pause_pump(self):
        """Pause pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state not in ["Infusing", "Withdrawing"]:
            raise InvalidValueError(
                f"Cannot pause from the current state ({curr_state})"
            )
        self._put_pv("pause", 4)

    @usermethod
    def resume_pump(self):
        """Resume pumping"""
        if self._mode == SIMULATION:
            return
        curr_state = self._attached_status.read(0)
        if curr_state != "Paused":
            self.log.warning("Resume request ignored as pump is not paused")
            return
        self._put_pv("pause", 5)

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        if param == self._record_fields["message"].cache_key:
            try:
                s = value if isinstance(value, str) else str(value)
            except Exception:
                s = ""
            self._cache.put(self._name, param, s, ts)

        self._cache.put(self._name, "status", self._do_status(), ts)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        # Cache alarm/status channel updates under the same cache key so
        # get_from_cache_or can still short-circuit reads if appropriate.
        ts = time.time()
        self._cache.put(self._name, param, value, ts)
        self._cache.put(self._name, "status", self._do_status(), ts)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        # Use the message PV as a canary for connection health
        canary = self._record_fields["message"].cache_key
        if param != canary:
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

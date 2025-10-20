import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Attach,
    Override,
    Param,
    Readable,
    oneof,
    pvname,
    status,
    usermethod,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class HPLCPumpController(EpicsParameters, MappedMoveable):
    """
    Device that controls an HPLC pump (new EpicsParameters-style).

    - Commands are exposed via MappedMoveable mapping (start/stop/volume_start/time_start).
    - `run_started` is a parameter tracking the initial-start busy transitional state.
    - Uses poller subscriptions for relevant PVs.
    """

    parameters = {
        "pv_root": Param("HPLC pump EPICS prefix", type=pvname, mandatory=True),
        "max_pressure": Param(
            "Maximum pressure", type=float, settable=True, volatile=True
        ),
        "min_pressure": Param(
            "Minimum pressure", type=float, settable=True, volatile=True
        ),
        "run_started": Param(
            "True while initial start transition is in progress",
            type=bool,
            default=False,
            settable=True,
            userparam=False,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, userparam=False),
        "mapping": Override(
            mandatory=False,
            settable=False,
            userparam=False,
            volatile=True,
        ),
    }

    attached_devices = {
        "status": Attach("Status of device", Readable),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            "error": RecordInfo("error", "Error-R", RecordType.STATUS),
            "error_text": RecordInfo("error_text", "ErrorText-R", RecordType.VALUE),
            "reset_error": RecordInfo("reset_error", "ErrorReset-S", RecordType.VALUE),
            "set_pressure_max": RecordInfo(
                "set_pressure_max", "PressureMax-S", RecordType.VALUE
            ),
            "pressure_max_rbv": RecordInfo(
                "pressure_max_rbv", "PressureMax-R", RecordType.VALUE
            ),
            "set_pressure_min": RecordInfo(
                "set_pressure_min", "PressureMin-S", RecordType.VALUE
            ),
            "pressure_min_rbv": RecordInfo(
                "pressure_min_rbv", "PressureMin-R", RecordType.VALUE
            ),
            "pump_for_time": RecordInfo(
                "pump_for_time", "PumpForTime-S", RecordType.VALUE
            ),
            "pump_for_volume": RecordInfo(
                "pump_for_volume", "PumpForVolume-S", RecordType.VALUE
            ),
            "start_pump": RecordInfo("start_pump", "Start-S", RecordType.VALUE),
            "stop_pump": RecordInfo("stop_pump", "Stop-S", RecordType.VALUE),
        }

        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)

        self._epics_wrapper.connect_pv(
            f"{self.pv_root}{self._record_fields['error_text'].pv_suffix}"
        )

    def doInit(self, mode):
        self._commands = {
            "start": self.start_pump,
            "volume_start": self.volume_start,
            "time_start": self.time_start,
            "stop": self.stop_pump,
        }
        cmd_mapping = {cmd: i for i, cmd in enumerate(self._commands.keys())}
        self._setROParam("mapping", cmd_mapping)

        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands.keys())

        if session.sessiontype == POLLER and self.monitor:
            for k, info in self._record_fields.items():
                full_pv = f"{self.pv_root}{info.pv_suffix}"
                if info.record_type in (RecordType.VALUE, RecordType.BOTH):
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            full_pv,
                            info.cache_key,
                            self._value_change_callback,
                            self._connection_change_callback,
                        )
                    )
                if info.record_type in (RecordType.STATUS, RecordType.BOTH):
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            full_pv,
                            info.cache_key,
                            self._status_change_callback,
                            self._connection_change_callback,
                        )
                    )

    def doPrepare(self):
        self._update_status(status.OK, "")

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        self._cache.put(self._name, param, value, ts)

        self._cache.put(self._name, "status", self._do_status(), ts)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        self._cache.put(self._name, param, value, ts)
        self._cache.put(self._name, "status", self._do_status(), ts)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        canary = self._record_fields["error_text"].cache_key
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

    def _pv(self, key: str) -> str:
        return f"{self.pv_root}{self._record_fields[key].pv_suffix}"

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

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        if self._mode == SIMULATION:
            return status.OK, ""

        # Check controller-reported error text
        try:
            device_msg = self._get_pv("error_text", as_string=True)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if device_msg not in ("No error", "[Program is Busy]"):
            return status.ERROR, device_msg

        # Attached status device (string like "Off"/"On"/etc.)
        attached_status, attached_msg = self._attached_status.status(0)
        attached_read = self._attached_status.read(0)

        # Transitional "start" busy phase
        if self.run_started:
            if attached_read == "Off":
                return status.BUSY, "Starting pump"
            else:
                # done with the transitional flag, now just running
                self._setROParam("run_started", False)
                return status.BUSY, attached_msg

        # If not Off, we are busy (running a program)
        if attached_read != "Off":
            return status.BUSY, attached_msg

        return attached_status, attached_msg

    def doRead(self, maxage=0):
        return self._attached_status.read(maxage)

    def doIsAtTarget(self, pos, target):
        # While transitional-flag is set, we're not "at target"
        if self.run_started:
            return False

        try:
            current = self._attached_status.read(0)
        except Exception:
            return False

        if target in ("start", "volume_start", "time_start"):
            # target reached when pump has *stopped* (i.e. program finished)
            return current == "Off"
        elif target == "stop":
            # target reached when it's *not* Off (i.e. was running → now stopping?)
            return current != "Off"
        return False

    def doStart(self, target):
        if target in self._commands:
            self._commands[target]()

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("stop_pump", 1)
        self._setROParam("run_started", False)

    def doReset(self):
        self._put_pv("reset_error", 1)

    def doReadMapping(self):
        return {cmd: i for i, cmd in enumerate(self._commands.keys())}

    def doReadMax_Pressure(self, maxage=0):
        return self._get_cached_pv_or_ask("pressure_max_rbv")

    def doWriteMax_Pressure(self, value):
        self._put_pv("set_pressure_max", value)

    def doReadMin_Pressure(self, maxage=0):
        return self._get_cached_pv_or_ask("pressure_min_rbv")

    def doWriteMin_Pressure(self, value):
        self._put_pv("set_pressure_min", value)

    @usermethod
    def start_pump(self):
        """Start pumping"""
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("start_pump", 1)

    @usermethod
    def stop_pump(self):
        """Stop pumping"""
        if self._mode == SIMULATION:
            return
        self._put_pv("stop_pump", 1)

    @usermethod
    def volume_start(self):
        """Start pumping for a given volume"""
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("pump_for_volume", 1)

    @usermethod
    def time_start(self):
        """Start pumping for a given time"""
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("pump_for_time", 1)

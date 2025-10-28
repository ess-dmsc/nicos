import threading
import time

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Override,
    Param,
    oneof,
    pvname,
    status,
    usermethod,
)
from nicos.devices.abstract import MappedMoveable
from nicos.utils import createThread
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class HPLCPumpController(EpicsParameters, MappedMoveable):
    """
    HPLC pump controller (EPICS PVA).

    - Commands via MappedMoveable values: start / volume_start / time_start / stop
    - `run_started` tracks transitional 'starting' phase
    - No attached status device; we derive everything from PVs
    - `Status-R` is an mbbi; we cache/operate on its **string** choice
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
            mandatory=False, settable=False, userparam=False, volatile=True
        ),
    }

    _STATE_OFF = "Off"
    _STATE_PUMPING = "Pumping"  # expected 'running' state from the IOC

    def doPreinit(self, mode):
        self._record_fields = {
            "error": RecordInfo("error", "Error-R", RecordType.STATUS),
            "error_text": RecordInfo("error_text", "ErrorText-R", RecordType.VALUE),
            "reset_error": RecordInfo("reset_error", "ErrorReset-S", RecordType.VALUE),
            "run_status": RecordInfo("run_status", "Status-R", RecordType.BOTH),  # mbbi
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

        # connect canary for connection-state messages
        self._epics_wrapper.connect_pv(
            f"{self.pv_root}{self._record_fields['error_text'].pv_suffix}"
        )
        # we will read choices from this mbbi PV, so connect early
        self._epics_wrapper.connect_pv(self._pv("run_status"))

        # mbbi choice list (index -> str)
        self._run_status_choices = None  # list[str] or None

    def doInit(self, mode):
        # Commands exposed to MappedMoveable
        self._commands = {
            "start": self.start_pump,
            "volume_start": self.volume_start,
            "time_start": self.time_start,
            "stop": self.stop_pump,
        }
        self._setROParam(
            "mapping", {cmd: i for i, cmd in enumerate(self._commands.keys())}
        )

        # load mbbi choices once
        self._refresh_run_status_choices()

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

    # ---------------- EPICS helpers

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

    # ---------------- mbbi handling

    def _refresh_run_status_choices(self):
        try:
            self._run_status_choices = (
                self._epics_wrapper.get_value_choices(self._pv("run_status")) or []
            )
        except Exception:
            self._run_status_choices = []

    def _map_run_status(self, value):
        """Normalize run_status to a string, using mbbi choices if value is int."""
        if isinstance(value, int) and self._run_status_choices:
            try:
                return self._run_status_choices[value]
            except Exception:
                pass
        # already a string (some backends do that) or unknown -> stringify
        return value if isinstance(value, str) else str(value)

    def _read_run_status_str(self):
        """Read current run_status as **string**, using cache if possible."""

        def _ask():
            # ask raw int to be safe across backends, then map
            raw = self._epics_wrapper.get_pv_value(
                self._pv("run_status"), as_string=False
            )
            # choices might not be loaded yet (early startup), try again on demand
            if not self._run_status_choices:
                self._refresh_run_status_choices()
            return self._map_run_status(raw)

        return get_from_cache_or(self, "run_status", _ask)

    # ---------------- wait-until utility (with mapping)

    def _wait_until(self, pv_name, expected_string, timeout=5.0):
        """Wait until the mbbi-backed PV equals the given **string** choice."""
        event = threading.Event()

        def callback(name, param, value, units, limits, severity, message, **kwargs):
            # ensure we have choices available and map to string
            if not self._run_status_choices and param == "run_status":
                self._refresh_run_status_choices()
            if self._map_run_status(value) == expected_string:
                event.set()

        sub = self._epics_wrapper.subscribe(self._pv(pv_name), pv_name, callback)
        try:
            # short-circuit if already there
            current_val = self._epics_wrapper.get_pv_value(
                self._pv(pv_name), as_string=False
            )
            if self._map_run_status(current_val) == expected_string:
                return
            if not event.wait(timeout):
                raise TimeoutError(
                    f"Timeout waiting for {pv_name} to become {expected_string}"
                )
        finally:
            self._epics_wrapper.close_subscription(sub)

    # ---------------- Status / completion

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        if self._mode == SIMULATION:
            return status.OK, ""

        # 1) controller-reported error
        try:
            device_msg = self._get_pv("error_text", as_string=True)
        except TimeoutError:
            return status.ERROR, "timeout reading status"
        if device_msg not in ("No error", "[Program is Busy]"):
            return status.ERROR, device_msg

        # 2) derive from run_status (mbbi -> string)
        try:
            run_state = self._read_run_status_str()
        except TimeoutError:
            return status.ERROR, "timeout reading run status"

        # transitional phase: we set run_started in the usermethod/doStart.
        # clear as soon as IOC leaves "Off"; otherwise show 'Starting pump'.
        if self.run_started:
            if run_state == self._STATE_OFF:
                return status.BUSY, "Starting pump"
            else:
                self._setROParam("run_started", False)
                return status.BUSY, run_state

        # running if not Off
        if run_state != self._STATE_OFF:
            return status.BUSY, run_state

        # idle
        return status.OK, run_state

    def doIsAtTarget(self, pos, target):
        if self.run_started:
            return False

        try:
            current = self._read_run_status_str()
        except Exception:
            return False

        if target in ("start", "volume_start", "time_start"):
            # done when program finished -> back to Off
            return current == self._STATE_OFF
        elif target == "stop":
            # done when Off
            return current == self._STATE_OFF
        return False

    # ---------------- NICOS start/stop entry points

    def doStart(self, target):
        # execute mapped command
        if target in self._commands:
            self._commands[target]()

            # kick a guard thread that waits for **Pumping** explicitly.
            # we ALSO clear run_started in the subscription as soon as we see != Off,
            # so this is just a fallback to avoid getting stuck forever.
            if target in ("start", "volume_start", "time_start"):

                def monitor_run_start():
                    try:
                        self._wait_until(
                            "run_status", self._STATE_PUMPING, timeout=10.0
                        )
                    except TimeoutError:
                        self.log.error(
                            "Timeout waiting for pump to report %r", self._STATE_PUMPING
                        )
                    finally:
                        # ensure the flag cannot stick
                        self.run_started = False

                createThread(
                    f"hplc_pump_run_start_monitor_{self._name}", monitor_run_start
                )

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("stop_pump", 1)
        self._setROParam("run_started", False)

    def doReset(self):
        self._put_pv("reset_error", 1)

    def doRead(self, maxage=0):
        return self.target

    def doReadMapping(self):
        return {cmd: i for i, cmd in enumerate(self._commands.keys())}

    # ---------------- Pressure parameters

    def doReadMax_Pressure(self, maxage=0):
        return self._get_cached_pv_or_ask("pressure_max_rbv")

    def doWriteMax_Pressure(self, value):
        self._put_pv("set_pressure_max", value)

    def doReadMin_Pressure(self, maxage=0):
        return self._get_cached_pv_or_ask("pressure_min_rbv")

    def doWriteMin_Pressure(self, value):
        self._put_pv("set_pressure_min", value)

    # ---------------- User methods (set transitional flag & trigger EPICS)

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

    # ---------------- Callbacks

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()

        # normalize run_status to string (mbbi) before caching
        if param == "run_status":
            if not self._run_status_choices:
                self._refresh_run_status_choices()
            vstr = self._map_run_status(value)
            self._cache.put(self._name, param, vstr, ts)

            # clear transitional flag as soon as IOC leaves Off
            if self.run_started and vstr != self._STATE_OFF:
                self._setROParam("run_started", False)
        else:
            self._cache.put(self._name, param, value, ts)

        self._cache.put(self._name, "status", self._do_status(), ts)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        # keep raw status updates (we only normalize VALUE stream for run_status)
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

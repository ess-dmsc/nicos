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

    - Commands via MappedMoveable values: start / volume_start / time_start / stop.
    - `run_started` tracks the transitional 'starting' phase until IOC leaves "Off".
    - No attached status device: derive state from EPICS PVs directly.
    - Normalize mbbi records (Status-R, Error-R) to **strings** in the cache.
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
    _STATE_PUMPING = "Pumping"  # for the guard waiter; BUSY is any != "Off"

    def doPreinit(self, mode):
        self._record_fields = {
            # Use BOTH for Error-R so we can read its enum value (not only alarm)
            "error": RecordInfo("error", "Error-R", RecordType.BOTH),
            "error_text": RecordInfo("error_text", "ErrorText-R", RecordType.VALUE),
            "reset_error": RecordInfo("reset_error", "ErrorReset-S", RecordType.VALUE),
            # mbbi with human-readable choices
            "run_status": RecordInfo("run_status", "Status-R", RecordType.BOTH),
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

        # Connect PVs we rely on for connection messages and choices
        self._epics_wrapper.connect_pv(self._pv("error_text"))
        self._epics_wrapper.connect_pv(self._pv("run_status"))
        self._epics_wrapper.connect_pv(self._pv("error"))

        # enum choice caches
        self._run_status_choices = []
        self._error_choices = []

    def doInit(self, mode):
        self._commands = {
            "start": self.start_pump,
            "volume_start": self.volume_start,
            "time_start": self.time_start,
            "stop": self.stop_pump,
        }
        self._setROParam(
            "mapping", {cmd: i for i, cmd in enumerate(self._commands.keys())}
        )

        # Load enum choices once
        self._refresh_choices()

        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands.keys())

        if session.sessiontype == POLLER and self.monitor:
            for k, info in self._record_fields.items():
                full_pv = self._pv(k)
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

    # ---------------- helpers

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

    def _refresh_choices(self):
        try:
            self._run_status_choices = (
                self._epics_wrapper.get_value_choices(self._pv("run_status")) or []
            )
        except Exception:
            self._run_status_choices = []
        try:
            self._error_choices = (
                self._epics_wrapper.get_value_choices(self._pv("error")) or []
            )
        except Exception:
            self._error_choices = []

    def _map_enum(self, idx_or_str, choices):
        if isinstance(idx_or_str, int) and choices:
            try:
                return choices[idx_or_str]
            except Exception:
                return str(idx_or_str)
        return idx_or_str if isinstance(idx_or_str, str) else str(idx_or_str)

    def _read_run_status_str(self):
        """Return run status as string from cache (normalized in value callback)."""

        def _ask():
            raw = self._epics_wrapper.get_pv_value(
                self._pv("run_status"), as_string=False
            )
            if not self._run_status_choices:
                self._refresh_choices()
            return self._map_enum(raw, self._run_status_choices)

        return get_from_cache_or(self, "run_status", _ask)

    def _read_error_str(self):
        """Return error enum as string (from Error-R)."""

        def _ask():
            raw = self._epics_wrapper.get_pv_value(self._pv("error"), as_string=False)
            if not self._error_choices:
                self._refresh_choices()
            return self._map_enum(raw, self._error_choices)

        return get_from_cache_or(self, "error", _ask)

    def _wait_until(self, pv_name, expected_string, timeout=5.0):
        """Wait until mbbi PV equals given **string**."""
        event = threading.Event()

        def callback(name, param, value, units, limits, severity, message, **kwargs):
            if param == "run_status" and not self._run_status_choices:
                self._refresh_choices()
            if self._map_enum(value, self._run_status_choices) == expected_string:
                event.set()

        sub = self._epics_wrapper.subscribe(self._pv(pv_name), pv_name, callback)
        try:
            cur = self._epics_wrapper.get_pv_value(self._pv(pv_name), as_string=False)
            if self._map_enum(cur, self._run_status_choices) == expected_string:
                return
            if not event.wait(timeout):
                raise TimeoutError(
                    f"Timeout waiting for {pv_name} to become {expected_string}"
                )
        finally:
            self._epics_wrapper.close_subscription(sub)

    # ---------------- NICOS status API

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        if self._mode == SIMULATION:
            return status.OK, ""

        # Use Error-R (enum) as authoritative error indicator
        try:
            err = self._read_error_str()
        except TimeoutError:
            return status.ERROR, "timeout reading error state"

        if err and err != "No error":
            # Don't block on ErrorText-R, it might lag/never clear
            return status.ERROR, err

        # No current error → derive state from Status-R
        try:
            run_state = self._read_run_status_str()
        except TimeoutError:
            return status.ERROR, "timeout reading run status"

        if self.run_started:
            if run_state == self._STATE_OFF:
                return status.BUSY, "Starting pump"
            else:
                self._setROParam("run_started", False)
                return status.BUSY, run_state

        if run_state != self._STATE_OFF:
            return status.BUSY, run_state

        return status.OK, run_state

    def doIsAtTarget(self, pos, target):
        if self.run_started:
            return False
        try:
            current = self._read_run_status_str()
        except Exception:
            return False

        if target in ("start", "volume_start", "time_start", "stop"):
            # finish when pump is Off
            return current == self._STATE_OFF
        return False

    # ---------------- NICOS move lifecycle

    def doStart(self, target):
        if target in self._commands:
            self._commands[target]()

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
                        self._setROParam("run_started", False)

                createThread(
                    f"hplc_pump_run_start_monitor_{self._name}", monitor_run_start
                )

    def doFinish(self):
        self.doStop()

    def doStop(self):
        self._put_pv("stop_pump", 1)
        self._setROParam("run_started", False)

    def doReset(self):
        # Acknowledge/reset; ErrorText-R may still show old text, but doStatus uses Error-R.
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
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("start_pump", 1)

    @usermethod
    def stop_pump(self):
        if self._mode == SIMULATION:
            return
        self._put_pv("stop_pump", 1)

    @usermethod
    def volume_start(self):
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._put_pv("pump_for_volume", 1)

    @usermethod
    def time_start(self):
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

        if param == "run_status":
            if not self._run_status_choices:
                self._refresh_choices()
            vstr = self._map_enum(value, self._run_status_choices)
            self._cache.put(self._name, param, vstr, ts)

            # Fast-path: clear transitional flag as soon as IOC leaves Off
            if self.run_started and vstr != self._STATE_OFF:
                self._setROParam("run_started", False)

        elif param == "error":
            if not self._error_choices:
                self._refresh_choices()
            estr = self._map_enum(value, self._error_choices)
            self._cache.put(self._name, param, estr, ts)

        else:
            self._cache.put(self._name, param, value, ts)

        self._cache.put(self._name, "status", self._do_status(), ts)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        ts = time.time()
        # IMPORTANT: do NOT clobber the normalized enum cache for mbbi fields.
        if param not in ("run_status", "error"):
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

import time

from nicos.core import (
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
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelInfo,
    EpicsChannelRole,
    EpicsDeviceBase,
)


class HPLCPumpController(EpicsDeviceBase, MappedMoveable):
    """
    HPLC pump controller (EPICS PVA).

    - Commands via MappedMoveable values: start / volume_start / time_start / stop.
    - `run_started` tracks the transitional 'starting' phase until IOC leaves "Off".
    - No attached status device: derive state from EPICS PVs directly.
    - mbbi records (Status-R, Error-R) are cached as **strings** via as_string.
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
        "mapping": Override(mandatory=False, userparam=False, volatile=True),
    }

    _STATE_OFF = "Off"
    _STATE_PUMPING = "Pumping"  # for the start waiter; BUSY is any != "Off"

    _default_pv_root_attr = "pv_root"
    _primary_channel = "run_status"
    _epics_channels = {
        # Use VALUE_AND_STATUS for Error-R so we can read its enum value
        # (not only alarm)
        "error": EpicsChannelInfo(
            "error", "Error-R", EpicsChannelRole.VALUE_AND_STATUS, as_string=True
        ),
        "error_text": EpicsChannelInfo(
            "error_text", "ErrorText-R", EpicsChannelRole.VALUE, as_string=True
        ),
        "reset_error": EpicsChannelInfo(
            "", "ErrorReset-S", EpicsChannelRole.VALUE, subscribe=False
        ),
        # mbbi with human-readable choices
        "run_status": EpicsChannelInfo(
            "run_status", "Status-R", EpicsChannelRole.VALUE_AND_STATUS, as_string=True
        ),
        "set_pressure_max": EpicsChannelInfo(
            "", "PressureMax-S", EpicsChannelRole.VALUE, subscribe=False
        ),
        "pressure_max_rbv": EpicsChannelInfo(
            "pressure_max_rbv", "PressureMax-R", EpicsChannelRole.VALUE
        ),
        "set_pressure_min": EpicsChannelInfo(
            "", "PressureMin-S", EpicsChannelRole.VALUE, subscribe=False
        ),
        "pressure_min_rbv": EpicsChannelInfo(
            "pressure_min_rbv", "PressureMin-R", EpicsChannelRole.VALUE
        ),
        "pump_for_time": EpicsChannelInfo(
            "", "PumpForTime-S", EpicsChannelRole.VALUE, subscribe=False
        ),
        "pump_for_volume": EpicsChannelInfo(
            "", "PumpForVolume-S", EpicsChannelRole.VALUE, subscribe=False
        ),
        "start_pump": EpicsChannelInfo(
            "", "Start-S", EpicsChannelRole.VALUE, subscribe=False
        ),
        "stop_pump": EpicsChannelInfo(
            "", "Stop-S", EpicsChannelRole.VALUE, subscribe=False
        ),
    }

    def doPreinit(self, mode):
        self._commands = {
            "start": self.start_pump,
            "volume_start": self.volume_start,
            "time_start": self.time_start,
            "stop": self.stop_pump,
        }
        EpicsDeviceBase.doPreinit(self, mode)

    def _after_subscribe(self, mode):
        self._setROParam(
            "mapping", {cmd: i for i, cmd in enumerate(self._commands.keys())}
        )
        MappedMoveable.doInit(self, mode)
        self.valuetype = oneof(*self._commands.keys())

    def doPrepare(self):
        self._update_status(status.OK, "")

    def _update_status(self, new_status, message):
        self._cache.put(self._name, "status", (new_status, message), time.time())

    def _compute_status(self, maxage=0):
        if self._mode == SIMULATION:
            return status.OK, ""

        # Use Error-R (enum) as authoritative error indicator
        try:
            err = self._read_channel_cached("error", maxage=maxage) or ""
        except TimeoutError:
            return status.UNKNOWN, "timeout reading error state"

        if err and err != "No error":
            # Don't block on ErrorText-R, it might lag/never clear
            return status.ERROR, err

        # No current error → derive state from Status-R
        try:
            run_state = self._read_channel_cached("run_status", maxage=maxage)
        except TimeoutError:
            return status.UNKNOWN, "timeout reading run status"

        if self.run_started:
            if run_state == self._STATE_OFF:
                return status.BUSY, "Starting pump"
            self._setROParam("run_started", False)
            return status.BUSY, run_state

        if run_state != self._STATE_OFF:
            return status.BUSY, run_state

        return status.OK, run_state

    def doIsAtTarget(self, pos, target):
        if self.run_started:
            return False
        try:
            current = self._read_channel_cached("run_status")
        except Exception:
            return False

        if target in ("start", "volume_start", "time_start", "stop"):
            # finish when pump is Off
            return current == self._STATE_OFF
        return False

    def doStart(self, target):
        if target in self._commands:
            self._commands[target]()

            if target in ("start", "volume_start", "time_start"):
                # It takes a few seconds before the pump actually starts pumping.
                # Start a monitor thread to clear the 'run_started' flag when that
                # happens. 'run_started' indicates the transitional starting phase.

                def monitor_run_start():
                    try:
                        self._epics.wait_for(
                            "run_status", self._STATE_PUMPING, timeout=10.0
                        )
                    except TimeoutError:
                        self.log.error(
                            "Timeout waiting for pump to report %r",
                            self._STATE_PUMPING,
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
        self._epics.put_channel_value("stop_pump", 1)
        self._setROParam("run_started", False)

    def doReset(self):
        # Acknowledge/reset; ErrorText-R may still show old text, but the
        # status computation uses Error-R.
        self._epics.put_channel_value("reset_error", 1)

    def doRead(self, maxage=0):
        return self.target

    def doReadMapping(self):
        return {cmd: i for i, cmd in enumerate(self._commands.keys())}

    def doReadMax_Pressure(self):
        return self._epics.get_channel_value("pressure_max_rbv")

    def doWriteMax_Pressure(self, value):
        self._epics.put_channel_value("set_pressure_max", value)

    def doReadMin_Pressure(self):
        return self._epics.get_channel_value("pressure_min_rbv")

    def doWriteMin_Pressure(self, value):
        self._epics.put_channel_value("set_pressure_min", value)

    @usermethod
    def start_pump(self):
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._epics.put_channel_value("start_pump", 1)

    @usermethod
    def stop_pump(self):
        if self._mode == SIMULATION:
            return
        self._epics.put_channel_value("stop_pump", 1)

    @usermethod
    def volume_start(self):
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._epics.put_channel_value("pump_for_volume", 1)

    @usermethod
    def time_start(self):
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._epics.put_channel_value("pump_for_time", 1)

    def _value_change_callback(
        self, pv_name, channel, value, units, limits, severity, message, **kwargs
    ):
        # Fast-path: clear transitional flag as soon as IOC leaves Off
        if channel == "run_status" and self.run_started and value != self._STATE_OFF:
            self._setROParam("run_started", False)
        super()._value_change_callback(
            pv_name, channel, value, units, limits, severity, message, **kwargs
        )

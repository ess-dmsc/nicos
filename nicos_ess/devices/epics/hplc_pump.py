import time

from nicos.core import (
    SIMULATION,
    CommunicationError,
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
    EpicsDeviceBase,
    command_channel,
    readback_channel,
    status_channel,
)


class HPLCPumpController(EpicsDeviceBase, MappedMoveable):
    """HPLC pump controller for the ESS EPICS PVA pump PVs."""

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

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "run_status"
    _epics_channels = {
        "error": status_channel("Error-R", cache_key="error", as_string=True),
        "error_text": readback_channel(
            "ErrorText-R",
            cache_key="error_text",
            as_string=True,
            subscribe=False,
            connect_on_startup=False,
        ),
        "reset_error": command_channel("ErrorReset-S"),
        "run_status": readback_channel(
            "Status-R",
            cache_key="run_status",
            as_string=True,
            primary=True,
        ),
        "set_pressure_max": command_channel("PressureMax-S"),
        "pressure_max_rbv": readback_channel("PressureMax-R", cache_key="max_pressure"),
        "set_pressure_min": command_channel("PressureMin-S"),
        "pressure_min_rbv": readback_channel("PressureMin-R", cache_key="min_pressure"),
        "pump_for_time": command_channel("PumpForTime-S"),
        "pump_for_volume": command_channel("PumpForVolume-S"),
        "start_pump": command_channel("Start-S"),
        "stop_pump": command_channel("Stop-S"),
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

        try:
            err = self._read_channel_cached("error", maxage=maxage) or ""
        except (TimeoutError, CommunicationError):
            return status.UNKNOWN, "timeout reading error state"

        if err and err != "No error":
            return status.ERROR, err

        try:
            run_state = self._read_channel_cached("run_status", maxage=maxage)
        except (TimeoutError, CommunicationError):
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
            return current == self._STATE_OFF
        return False

    def doStart(self, target):
        if target in self._commands:
            self._commands[target]()

            if target in ("start", "volume_start", "time_start"):

                def monitor_run_start():
                    try:
                        self._epics.wait_for(
                            "run_status", self._STATE_PUMPING, timeout=10.0
                        )
                    except (TimeoutError, CommunicationError):
                        self.log.error(
                            "Timeout waiting for pump to report %r",
                            self._STATE_PUMPING,
                        )
                    finally:
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
        """Start the pump in continuous mode."""
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._epics.put_channel_value("start_pump", 1)

    @usermethod
    def stop_pump(self):
        """Stop the pump."""
        if self._mode == SIMULATION:
            return
        self._epics.put_channel_value("stop_pump", 1)

    @usermethod
    def volume_start(self):
        """Start the pump until the set volume has been pumped."""
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._epics.put_channel_value("pump_for_volume", 1)

    @usermethod
    def time_start(self):
        """Start the pump for the set amount of time."""
        if self._mode == SIMULATION:
            return
        self._setROParam("run_started", True)
        self._update_status(status.BUSY, "Starting pump")
        self._epics.put_channel_value("pump_for_time", 1)

    def _on_channel_update(self, update):
        if (
            update.channel == "run_status"
            and self.run_started
            and update.value != self._STATE_OFF
        ):
            self._setROParam("run_started", False)
        super()._on_channel_update(update)

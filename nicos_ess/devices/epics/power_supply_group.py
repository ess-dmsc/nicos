import time
from copy import copy

from nicos.core import (
    ADMIN,
    SIMULATION,
    ConfigurationError,
    HasPrecision,
    LimitError,
    Moveable,
    MoveError,
    Override,
    Param,
    Value,
    floatrange,
    none_or,
    requires,
    status,
    tupleof,
    usermethod,
)
from nicos_ess.devices.epics.pva.epics_common import (
    command_channel,
    readback_channel,
    status_channel,
    worst_status,
)
from nicos_ess.devices.epics.pva.epics_multisource import EpicsMultiSourceBase
from nicos_ess.devices.mixins import EventDrivenCanDisable

_STATUS_CHANNELS = {
    "status_on": (0, "-Status-ON"),
    "status_ramping_up": (1, "-Status-RU"),
    "status_ramping_down": (2, "-Status-RD"),
    "status_over_current": (3, "-Status-OC"),
    "status_over_voltage": (4, "-Status-OV"),
    "status_under_voltage": (5, "-Status-UV"),
    "status_external_trip": (6, "-Status-ET"),
    "status_max_voltage": (7, "-Status-MV"),
    "status_external_disable": (8, "-Status-ED"),
    "status_internal_trip": (9, "-Status-IT"),
    "status_calibration_error": (10, "-Status-CE"),
    "status_unplugged": (11, "-Status-UN"),
}


class PowerSupplyGroup(
    EpicsMultiSourceBase, EventDrivenCanDisable, HasPrecision, Moveable
):
    """A group of CAEN SYx527 channels operated as one NICOS device."""

    parameters = {
        "currents": Param(
            "Monitored output current for each channel",
            type=float,
            settable=False,
            volatile=True,
            unit="",
            fmtstr="%.3g",
        ),
        "current_limits": Param(
            "Configured output-current limit for each channel",
            type=float,
            settable=True,
            volatile=True,
            unit="",
            fmtstr="%.3g",
            chatty=True,
        ),
        "voltage_off_threshold": Param(
            "Largest absolute output voltage considered safely off; "
            "None disables the voltage check",
            type=none_or(floatrange(0)),
            default=None,
            unit="main",
            fmtstr="main",
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
        "fmtstr": Override(default="%.3f", settable=False),
    }

    _epics_channels = {
        "voltage": readback_channel("-VMon"),
        "setpoint": readback_channel("-V0Set-RB"),
        "setpoint_command": command_channel("-V0Set"),
        "current": readback_channel("-IMon"),
        "current_limit": readback_channel("-I0Set-RB"),
        "current_limit_command": command_channel("-I0Set"),
        "power_readback": readback_channel("-Pw-RB", connect_on_startup=False),
        "power": command_channel("-Pw"),
        **{
            channel: status_channel(
                suffix, refresh_status=False, connect_on_startup=False
            )
            for channel, (_bit, suffix) in _STATUS_CHANNELS.items()
        },
    }

    _warning_bits = {
        5: "under voltage",
        8: "externally disabled",
    }
    _error_bits = {
        3: "over current",
        4: "over voltage",
        6: "external trip",
        7: "maximum voltage",
        9: "internal trip",
        10: "calibration error",
        11: "unplugged",
    }

    errorstates = {**Moveable.errorstates, status.UNKNOWN: MoveError}

    def init(self):
        source_count = len(self._config.get("sources", ()))
        current_type = (
            float
            if source_count <= 1
            else tupleof(*(float for _ in range(source_count)))
        )
        parameters = dict(self.parameters)
        for name in ("currents", "current_limits"):
            info = copy(parameters[name])
            info.type = current_type
            info.default = current_type()
            parameters[name] = info
        self.__dict__["parameters"] = parameters
        super().init()

    def doPreinit(self, mode):
        if not self.sources:
            raise ConfigurationError(self, "a power-supply group cannot be empty")
        if len(set(self.sources.values())) != len(self.sources):
            raise ConfigurationError(
                self, "each power-supply channel PV prefix must be unique"
            )

        self._source_ids = tuple(self.sources)
        self.valuetype = (
            float
            if len(self._source_ids) == 1
            else tupleof(*(float for _ in self._source_ids))
        )
        self._seen_updates = set()
        self._voltages = {}
        self._setpoints = {}
        self._currents = {}
        self._current_limits = {}
        self._power_states = {}
        self._status_words = {}
        self._alarm_states = {}
        self._last_status_signature = None
        super().doPreinit(mode)

        if mode != SIMULATION:
            voltage_units = self._units_for("voltage", "setpoint", "setpoint_command")
            if len(voltage_units) != 1:
                raise ConfigurationError(
                    self,
                    "all voltage readbacks and setpoints must use the same unit; "
                    f"found {sorted(voltage_units)!r}",
                )
            current_units = self._units_for(
                "current", "current_limit", "current_limit_command"
            )
            if len(current_units) != 1:
                raise ConfigurationError(
                    self,
                    "all current readbacks and limits must use the same unit; "
                    f"found {sorted(current_units)!r}",
                )
            current_unit = current_units.pop()
            self.parameters["currents"].unit = current_unit
            self.parameters["current_limits"].unit = current_unit

    def _units_for(self, *channels):
        return {
            self._epics.get_source_units(source_id, channel)
            for source_id in self._source_ids
            for channel in channels
        }

    def _as_tuple(self, value):
        if len(self._source_ids) == 1:
            return (float(value),)
        return tuple(value)

    def _as_value(self, values):
        ordered = tuple(values[source_id] for source_id in self._source_ids)
        return ordered[0] if len(ordered) == 1 else ordered

    def _all_monitors_seen(self):
        subscribed = sum(info.subscribe for info in self._epics_channels.values())
        return len(self._seen_updates) == len(self.sources) * subscribed

    def _voltages_are_off(self, voltage):
        threshold = self.voltage_off_threshold
        return threshold is None or all(
            abs(actual) <= threshold for actual in self._as_tuple(voltage)
        )

    def _on_channel_update(self, update):
        timestamp = time.time()
        key = update.source_id, update.channel
        self._seen_updates.add(key)
        self._alarm_states[key] = update.severity, update.message

        if update.channel == "voltage":
            self._voltages[update.source_id] = float(update.value)
        elif update.channel == "setpoint":
            self._setpoints[update.source_id] = float(update.value)
        elif update.channel == "current":
            self._currents[update.source_id] = float(update.value)
        elif update.channel == "current_limit":
            self._current_limits[update.source_id] = float(update.value)
        elif update.channel == "power_readback":
            self._power_states[update.source_id] = bool(int(update.value))
        elif update.channel in _STATUS_CHANNELS:
            bit, _suffix = _STATUS_CHANNELS[update.channel]
            mask = 1 << bit
            word = self._status_words.get(update.source_id, 0)
            if int(update.value):
                word |= mask
            else:
                word &= ~mask
            self._status_words[update.source_id] = word

        super()._on_channel_update(update)

        if len(self._voltages) == len(self.sources):
            self._cache.put(
                self._name, "value", self._as_value(self._voltages), timestamp
            )
        if len(self._setpoints) == len(self.sources):
            self._cache.put(
                self._name, "target", self._as_value(self._setpoints), timestamp
            )
        if len(self._currents) == len(self.sources):
            self._cache.put(
                self._name, "currents", self._as_value(self._currents), timestamp
            )
        if len(self._current_limits) == len(self.sources):
            self._cache.put(
                self._name,
                "current_limits",
                self._as_value(self._current_limits),
                timestamp,
            )

        signature = self._status_signature()
        if signature is not None and signature != self._last_status_signature:
            self._last_status_signature = signature
            self._refresh_status(timestamp)

    def _on_connection_change(self, change):
        super()._on_connection_change(change)
        if not change.is_connected:
            self._seen_updates.discard((change.source_id, change.channel))
            self._last_status_signature = None

    def _status_signature(self):
        if not self._all_monitors_seen():
            return None
        powered = all(word & 1 for word in self._status_words.values())
        at_target = powered and self.doIsAtTarget(
            self._as_value(self._voltages), self._as_value(self._setpoints)
        )
        voltages_are_off = self._voltages_are_off(self._as_value(self._voltages))
        return (
            tuple(self._status_words.items()),
            tuple(self._power_states.items()),
            tuple(self._alarm_states.items()),
            at_target,
            voltages_are_off,
        )

    def _read_values(self, channel, maxage):
        return {
            source_id: float(self._read_source(source_id, channel, maxage))
            for source_id in self._source_ids
        }

    def _read_status_words(self, maxage):
        words = {}
        for source_id in self._source_ids:
            word = 0
            for channel, (bit, _suffix) in _STATUS_CHANNELS.items():
                if int(self._read_source(source_id, channel, maxage)):
                    word |= 1 << bit
            words[source_id] = word
        return words

    def _read_power_states(self, maxage):
        return {
            source_id: bool(int(self._read_source(source_id, "power_readback", maxage)))
            for source_id in self._source_ids
        }

    def doRead(self, maxage=0):
        return self._as_value(self._read_values("voltage", maxage))

    def doReadTarget(self):
        return self._as_value(self._read_values("setpoint", None))

    def doReadCurrents(self):
        return self._as_value(self._read_values("current", None))

    def doReadCurrent_Limits(self):
        return self._as_value(self._read_values("current_limit", None))

    def doReadUnit(self):
        return self._epics.get_source_units(self._source_ids[0], "voltage")

    def valueInfo(self):
        return tuple(
            Value(source_id, unit=self.unit, fmtstr=self.fmtstr)
            for source_id in self._source_ids
        )

    def _limits_allow(self, channel, values):
        for source_id, value in zip(self._source_ids, self._as_tuple(values)):
            low, high = self._epics.get_source_limits(source_id, channel)
            if not low <= value <= high:
                return False, f"{source_id} limits are [{low}, {high}]"
        return True, ""

    def doIsAllowed(self, target):
        return self._limits_allow("setpoint_command", target)

    def doIsAtTarget(self, pos, target):
        if target is None:
            return True
        return all(
            abs(actual - wanted) <= self.precision
            for actual, wanted in zip(self._as_tuple(pos), self._as_tuple(target))
        )

    def doStart(self, target):
        for source_id, value in zip(self._source_ids, self._as_tuple(target)):
            self._put_source(source_id, "setpoint_command", value)

    def doWriteCurrent_Limits(self, values):
        previous = self.current_limits
        if self.fixed:
            if values != previous:
                self.log.warning(
                    "device fixed, not changing current limits: %s", self.fixed
                )
            return previous

        allowed, reason = self._limits_allow("current_limit_command", values)
        if not allowed:
            raise LimitError(self, f"changing current limits is not allowed: {reason}")
        for source_id, value in zip(self._source_ids, self._as_tuple(values)):
            self._put_source(source_id, "current_limit_command", value)
        return values

    def doEnable(self, on):
        for source_id in self._source_ids:
            self._put_source(source_id, "power", int(on))

    @usermethod
    @requires(level=ADMIN)
    def fix(self, reason=""):
        return super().fix(reason)

    @usermethod
    @requires(level=ADMIN)
    def release(self):
        return super().release()

    def _fault_status(self, words):
        warnings = []
        errors = []
        for source_id, word in words.items():
            warnings.extend(
                f"{source_id}: {label}"
                for bit, label in self._warning_bits.items()
                if word & (1 << bit)
            )
            errors.extend(
                f"{source_id}: {label}"
                for bit, label in self._error_bits.items()
                if word & (1 << bit)
            )
        if errors:
            return status.ERROR, "; ".join(errors)
        if warnings:
            return status.WARN, "; ".join(warnings)
        return status.OK, ""

    def _output_status(self, words, power_states, voltage, setpoint):
        channel_count = len(words)
        requested_on = sum(power_states.values())
        channels_on = sum(bool(word & 1) for word in words.values())
        ramping_up = sum(bool(word & 0b010) for word in words.values())
        ramping_down = sum(bool(word & 0b100) for word in words.values())
        ramping = ramping_up + ramping_down

        if not requested_on:
            if channels_on or ramping_up:
                return status.BUSY, "waiting for outputs to disable"
            if self.voltage_off_threshold is not None:
                if not self._voltages_are_off(voltage):
                    threshold = f"{self.voltage_off_threshold:g}"
                    if self.unit:
                        threshold += f" {self.unit}"
                    return (
                        status.BUSY,
                        f"waiting for output voltages to fall to {threshold} or below",
                    )
                return status.DISABLED, "output disabled"
            if ramping_down:
                return status.BUSY, "waiting for outputs to disable"
            return status.DISABLED, "output disabled"
        if requested_on != channel_count:
            return (
                status.WARN,
                f"{requested_on} of {channel_count} outputs requested on",
            )
        if channels_on != channel_count:
            return status.BUSY, f"{channels_on} of {channel_count} outputs enabled"
        if ramping:
            return status.BUSY, f"{ramping} of {channel_count} outputs ramping"
        if not self.doIsAtTarget(voltage, setpoint):
            return status.BUSY, "voltage readback has not reached target"
        return status.OK, "output enabled"

    def _compute_status(self, maxage=0):
        if maxage is None:
            if not self._all_monitors_seen():
                return status.UNKNOWN, "waiting for EPICS channel data"
            words = dict(self._status_words)
            power_states = dict(self._power_states)
            voltage = self._as_value(self._voltages)
            setpoint = self._as_value(self._setpoints)
            hardware = worst_status(*self._alarm_states.values())
        else:
            words = self._read_status_words(maxage)
            power_states = self._read_power_states(maxage)
            voltage = self.doRead(maxage)
            setpoint = self._as_value(self._read_values("setpoint", maxage))
            hardware = super()._compute_status(maxage)

        device_status = self._output_status(words, power_states, voltage, setpoint)

        faults = self._fault_status(words)
        severity, _ = worst_status(hardware, faults, device_status)
        details = [device_status[1]]
        details.extend(
            detail
            for candidate_status, detail in (hardware, faults)
            if candidate_status != status.OK and detail
        )
        return severity, "; ".join(details)

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
    requires,
    status,
    tupleof,
    usermethod,
)
from nicos_ess.devices.epics.pva.epics_common import (
    command_channel,
    readback_channel,
    setpoint_channel,
    status_channel,
    worst_status,
)
from nicos_ess.devices.epics.pva.epics_multisource import EpicsMultiSourceBase
from nicos_ess.devices.mixins import EventDrivenCanDisable


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
    }

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=True),
        "fmtstr": Override(default="%.3f", settable=False),
    }

    _epics_channels = {
        "voltage": readback_channel("-VMon"),
        "setpoint": setpoint_channel("-V0Set"),
        "current": readback_channel("-IMon"),
        "current_limit": setpoint_channel("-I0Set"),
        "power": command_channel("-Pw"),
        "status_word": status_channel("-Status", refresh_status=False),
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
        self._status_words = {}
        self._alarm_states = {}
        self._last_status_signature = None
        super().doPreinit(mode)

        if mode != SIMULATION:
            current_units = {
                self._epics.get_source_units(source_id, channel)
                for source_id in self._source_ids
                for channel in ("current", "current_limit")
            }
            if len(current_units) != 1:
                raise ConfigurationError(
                    self,
                    "all current readbacks and limits must use the same unit; "
                    f"found {sorted(current_units)!r}",
                )
            current_unit = current_units.pop()
            self.parameters["currents"].unit = current_unit
            self.parameters["current_limits"].unit = current_unit

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
        elif update.channel == "status_word":
            self._status_words[update.source_id] = int(update.value)

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
        return (
            tuple(self._status_words.items()),
            tuple(self._alarm_states.items()),
            at_target,
        )

    def _read_values(self, channel, maxage):
        return {
            source_id: float(self._read_source(source_id, channel, maxage))
            for source_id in self._source_ids
        }

    def _read_status_words(self, maxage):
        return {
            source_id: int(self._read_source(source_id, "status_word", maxage))
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
        return self._limits_allow("setpoint", target)

    def doIsAtTarget(self, pos, target):
        if target is None:
            return True
        return all(
            abs(actual - wanted) <= self.precision
            for actual, wanted in zip(self._as_tuple(pos), self._as_tuple(target))
        )

    def doStart(self, target):
        for source_id, value in zip(self._source_ids, self._as_tuple(target)):
            self._put_source(source_id, "setpoint", value)

    def doWriteCurrent_Limits(self, values):
        previous = self.current_limits
        if self.fixed:
            if values != previous:
                self.log.warning(
                    "device fixed, not changing current limits: %s", self.fixed
                )
            return previous

        allowed, reason = self._limits_allow("current_limit", values)
        if not allowed:
            raise LimitError(self, f"changing current limits is not allowed: {reason}")
        for source_id, value in zip(self._source_ids, self._as_tuple(values)):
            self._put_source(source_id, "current_limit", value)
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

    def _compute_status(self, maxage=0):
        if maxage is None:
            if not self._all_monitors_seen():
                return status.UNKNOWN, "waiting for EPICS channel data"
            words = dict(self._status_words)
            voltage = self._as_value(self._voltages)
            setpoint = self._as_value(self._setpoints)
            hardware = worst_status(*self._alarm_states.values())
        else:
            words = self._read_status_words(maxage)
            voltage = self.doRead(maxage)
            setpoint = self._as_value(self._read_values("setpoint", maxage))
            hardware = super()._compute_status(maxage)

        channels_on = sum(bool(word & 1) for word in words.values())
        ramping = sum(bool(word & 0b110) for word in words.values())

        if not channels_on:
            device_status = status.DISABLED, "output disabled"
        elif channels_on != len(words):
            device_status = (
                status.WARN,
                f"{channels_on} of {len(words)} outputs enabled",
            )
        elif not self.doIsAtTarget(voltage, setpoint):
            device_status = status.BUSY, "voltage readback has not reached target"
        else:
            device_status = status.OK, "output enabled"

        faults = self._fault_status(words)
        severity, _ = worst_status(hardware, faults, device_status)
        details = [device_status[1]]
        details.extend(
            detail
            for candidate_status, detail in (hardware, faults)
            if candidate_status != status.OK and detail
        )
        if ramping:
            details.append(f"{ramping} channels ramping")
        return severity, "; ".join(details)

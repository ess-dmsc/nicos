import time
from copy import copy
from dataclasses import dataclass

from nicos.core import (
    ADMIN,
    SIMULATION,
    CanDisable,
    ConfigurationError,
    HasPrecision,
    LimitError,
    Moveable,
    MoveError,
    Override,
    Param,
    Value,
    anytype,
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

# Status bits driving the group's power and movement state.
_STATE_SUFFIXES = {
    "status_on": "-Status-ON",
    "status_ramping_up": "-Status-RU",
    "status_ramping_down": "-Status-RD",
}

# Channels whose per-channel values are published as one group cache key.
_GROUP_VALUES = {
    "voltage": "value",
    "current": "currents",
    "current_limit": "current_limits",
}


def _at_target(values, target, precision):
    return target is None or all(
        abs(actual - wanted) <= precision for actual, wanted in zip(values, target)
    )


@dataclass(frozen=True)
class SupplySnapshot:
    """Values and output counts from one complete group read.

    Status evaluation only uses these values and the supplied request/settings.
    It does not read EPICS, access the NICOS cache, or acknowledge commands.
    """

    voltages: tuple[float, ...]
    setpoints: tuple[float, ...]
    requested_on: int
    enabled: int
    ramping_up: int
    ramping_down: int
    alarm_status: tuple[int, str]

    @classmethod
    def from_readings(cls, readings, sources):
        def values(channel):
            return tuple(float(readings[source, channel][0]) for source in sources)

        def count(channel):
            return sum(bool(int(value)) for value in values(channel))

        # The IOC's -Status-Alarm record summarises all per-channel fault bits.
        faults = [
            f"{source}: alarm"
            for source in sources
            if int(readings[source, "status_alarm"][0])
        ]
        fault_status = (status.ERROR, "; ".join(faults)) if faults else (status.OK, "")
        return cls(
            voltages=values("voltage"),
            setpoints=values("setpoint"),
            requested_on=count("power_readback"),
            enabled=count("status_on"),
            ramping_up=count("status_ramping_up"),
            ramping_down=count("status_ramping_down"),
            alarm_status=worst_status(
                fault_status, *(alarm for _, alarm in readings.values())
            ),
        )

    @property
    def channel_count(self):
        return len(self.voltages)

    def status(self, *, target, pending_power, precision, voltage_off_threshold, unit):
        output = self._output_status(
            target, pending_power, precision, voltage_off_threshold, unit
        )
        return worst_status(output, self.alarm_status)

    def _output_status(self, target, pending_power, precision, off_threshold, unit):
        if pending_power is not None:
            expected_on = self.channel_count if pending_power else 0
            if self.requested_on != expected_on:
                action = "enable" if pending_power else "disable"
                return status.BUSY, f"waiting for outputs to {action}"

        if self.requested_on == 0:
            return self._off_status(off_threshold, unit)
        if self.requested_on != self.channel_count:
            return (
                status.WARN,
                f"{self.requested_on} of {self.channel_count} outputs requested on",
            )
        return self._on_status(target, precision)

    def _off_status(self, threshold, unit):
        if self.enabled or self.ramping_up:
            return status.BUSY, "waiting for outputs to disable"
        if threshold is None:
            if self.ramping_down:
                return status.BUSY, "waiting for outputs to disable"
        elif not all(abs(voltage) <= threshold for voltage in self.voltages):
            limit = f"{threshold:g} {unit}".strip()
            return (
                status.BUSY,
                f"waiting for output voltages to fall to {limit} or below",
            )
        # A configured voltage threshold decides when ramp-down is safe to ignore.
        return status.DISABLED, "output disabled"

    def _on_status(self, target, precision):
        if self.enabled != self.channel_count:
            return (
                status.BUSY,
                f"{self.enabled} of {self.channel_count} outputs enabled",
            )
        if self.ramping_up or self.ramping_down:
            count = self.ramping_up + self.ramping_down
            return status.BUSY, f"{count} of {self.channel_count} outputs ramping"
        if not _at_target(self.setpoints, target, precision):
            return status.BUSY, "waiting for voltage setpoints to update"
        if not _at_target(self.voltages, target, precision):
            return status.BUSY, "voltage readback has not reached target"
        return status.OK, "output enabled"


class CaenSyx527ChannelGroup(EpicsMultiSourceBase, CanDisable, HasPrecision, Moveable):
    """A group of CAEN SYx527 channels operated as one NICOS device.

    The channels are powered on and off together and report one status for the
    whole group. Value and target hold one entry per channel, ordered as the
    ``sources`` mapping declares them.

    Monitor updates land in the NICOS cache and the status is derived from
    there: ``maxage=None`` accepts cached values indefinitely, positive ages
    accept sufficiently recent values, and zero reads the IOC records directly.
    Fresh status reads batch all PVs and use each response for both its value
    and alarm. These records can themselves lag the hardware. Pending commands
    are shared through NICOS parameters until their readbacks acknowledge them.
    """

    parameters = {
        "pending_target": Param(
            "Voltage request awaiting setpoint readbacks",
            type=anytype,
            default=None,
            internal=True,
            prefercache=True,
        ),
        "pending_power": Param(
            "Power request awaiting power readbacks",
            type=none_or(bool),
            default=None,
            internal=True,
            prefercache=True,
        ),
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
        "unit": Override(mandatory=False, settable=False),
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
        "status_alarm": status_channel(
            "-Status-Alarm", refresh_status=False, connect_on_startup=False
        ),
        **{
            channel: status_channel(
                suffix, refresh_status=False, connect_on_startup=False
            )
            for channel, suffix in _STATE_SUFFIXES.items()
        },
    }

    errorstates = {**Moveable.errorstates, status.UNKNOWN: MoveError}

    def init(self):
        """Give this instance its own ``currents``/``current_limits`` Params.

        Their type depends on the number of sources and ``doPreinit`` fills in
        their unit from the IOC, so both must be per-instance rather than the
        class-level Param objects shared by every instance. NICOS validates
        against ``self.parameters`` at runtime, so the copies have to be
        installed before ``Device.init`` initialises any parameter.
        ``self.sources`` is not usable this early: its getter needs
        ``self._cache``, which ``Device.init`` is about to set.
        """
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

    def _group_value(self, values):
        """Expose a scalar for a single channel; keep tuples internally."""
        return values[0] if len(values) == 1 else values

    def _after_subscribe(self, mode):
        super()._after_subscribe(mode)
        if mode != SIMULATION and self.monitor and self._cache is not None:
            self._refresh_status(time.time())

    def _refresh_status(self, ts):
        """Publish the group status when it differs from what the cache holds.

        Every update of every subscribed PV lands here, far more often than the
        group status changes, and each publish is a cache write seen by every
        client. Reading the cache back also republishes a status that someone
        else invalidated.
        """
        snapshot = self._status_snapshot(maxage=None)
        if snapshot != self._cache.get(self._name, "status"):
            self._cache.put(self._name, "status", snapshot, ts)

    def _on_channel_update(self, update):
        timestamp = time.time()
        super()._on_channel_update(update)

        cache_key = _GROUP_VALUES.get(update.channel)
        if cache_key:
            values = tuple(
                self._cache.get(
                    self._name,
                    self._epics.source_key(source_id, update.channel),
                    Ellipsis,
                )
                for source_id in self._source_ids
            )
            if all(value is not Ellipsis for value in values):
                values = tuple(float(value) for value in values)
                self._cache.put(
                    self._name, cache_key, self._group_value(values), timestamp
                )
        self._refresh_status(timestamp)

    def _reconcile_requests(self, snapshot, *, acknowledge):
        """Update pending commands and return the effective target/power request.

        With monitors enabled, only a complete monitor snapshot may clear a
        request. A fresh read can complete a move before the monitors catch up;
        retaining the request prevents their older values restoring an old target.
        """
        pending_target = self.pending_target
        if (
            pending_target is not None
            and acknowledge
            and _at_target(
                snapshot.setpoints, self._as_tuple(pending_target), self.precision
            )
        ):
            self._setROParam("pending_target", None)
            pending_target = None

        target = (
            snapshot.setpoints
            if pending_target is None
            else self._as_tuple(pending_target)
        )
        public_target = self._group_value(target)
        if self.target != public_target:
            self._setROParam("target", public_target)

        pending_power = self.pending_power
        if pending_power is not None and acknowledge:
            expected_on = snapshot.channel_count if pending_power else 0
            if snapshot.requested_on == expected_on:
                self._setROParam("pending_power", None)
                pending_power = None
        return target, pending_power

    def _read_values(self, channel, maxage):
        """Read values in source order, honouring the requested cache age."""
        return tuple(
            float(self._read_source(source_id, channel, maxage))
            for source_id in self._source_ids
        )

    def _get_values(self, channel):
        """Per-channel values straight from the IOCs, for volatile params."""
        return tuple(
            float(self._epics.get_source_value(source_id, channel))
            for source_id in self._source_ids
        )

    def doRead(self, maxage=0):
        return self._group_value(self._read_values("voltage", maxage))

    def doReadTarget(self):
        return self._group_value(self._read_values("setpoint", None))

    def doReadCurrents(self):
        return self._group_value(self._get_values("current"))

    def doReadCurrent_Limits(self):
        return self._group_value(self._get_values("current_limit"))

    def doReadUnit(self):
        return self._epics.get_source_units(self._source_ids[0], "voltage")

    def valueInfo(self):
        return tuple(
            Value(
                self.name if len(self._source_ids) == 1 else f"{self.name}.{source_id}",
                unit=self.unit,
                fmtstr=self.fmtstr,
            )
            for source_id in self._source_ids
        )

    def _limits_allow(self, channel, values):
        if self._mode == SIMULATION:
            return True, ""
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
        return _at_target(self._as_tuple(pos), self._as_tuple(target), self.precision)

    def doStart(self, target):
        self._setROParam("pending_target", target)
        # A monitor may have updated target between Moveable.start and this hook.
        self._setROParam("target", target)
        for source_id, value in zip(self._source_ids, self._as_tuple(target)):
            self._put_source(source_id, "setpoint_command", value, wait=True)

    def doWriteCurrent_Limits(self, values):
        if self.fixed:
            previous = self.current_limits
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
        self._setROParam("pending_power", on)
        for source_id in self._source_ids:
            self._put_source(source_id, "power", int(on), wait=True)

    @usermethod
    @requires(level=ADMIN)
    def fix(self, reason=""):
        return super().fix(reason)

    @usermethod
    @requires(level=ADMIN)
    def release(self):
        return super().release()

    def _compute_status(self, maxage=0):
        readings = self._read_source_snapshot(
            maxage,
            cache_only=self.monitor and maxage is None and self._cache is not None,
        )
        total = len(self._source_ids) * sum(
            info.subscribe for info in self._epics_channels.values()
        )
        if len(readings) != total:
            return (
                status.UNKNOWN,
                f"waiting for EPICS data from {total - len(readings)} of {total} PVs",
            )

        snapshot = SupplySnapshot.from_readings(readings, self._source_ids)
        target, pending_power = self._reconcile_requests(
            snapshot, acknowledge=not self.monitor or maxage is None
        )
        return snapshot.status(
            target=target,
            pending_power=pending_power,
            precision=self.precision,
            voltage_off_threshold=self.voltage_off_threshold,
            unit=self.unit,
        )

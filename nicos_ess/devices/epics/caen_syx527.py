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

# Status bits driving the group's power and movement state.
_STATE_SUFFIXES = {
    "status_on": "-Status-ON",
    "status_ramping_up": "-Status-RU",
    "status_ramping_down": "-Status-RD",
}

# Channels the group status is computed from, one boolean per supply channel.
# "-Status-Alarm" is the IOC's OR of every per-channel fault bit (over
# current, over/under voltage, trips, calibration error, unplugged, ...), so
# the group monitors the summary and leaves the individual bits to the IOC
# screens.
_FLAG_CHANNELS = ("power_readback", "status_alarm", *_STATE_SUFFIXES)

# Channels whose per-channel values are published as one group cache key.
_GROUP_VALUES = {
    "voltage": "value",
    "setpoint": "target",
    "current": "currents",
    "current_limit": "current_limits",
}


class CaenSyx527ChannelGroup(
    EpicsMultiSourceBase, EventDrivenCanDisable, HasPrecision, Moveable
):
    """A group of CAEN SYx527 channels operated as one NICOS device.

    The channels are powered on and off together and report one status for the
    whole group. Value and target hold one entry per channel, ordered as the
    ``sources`` mapping declares them.

    Monitor updates land in the NICOS cache and the status is derived from
    there: ``maxage=None`` reads the cached per-channel values, any other
    maxage reads the IOCs, so ``status(0)`` reports what the hardware says
    right now. No channel state is kept on the device object, so every session
    computes the same status.
    """

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
        self._subscribed_keys = [
            self._epics.source_key(source_id, channel)
            for source_id in self._source_ids
            for channel, info in self._epics_channels.items()
            if info.subscribe
        ]
        self._cache_complete = False

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

    def _group_value(self, per_source):
        ordered = tuple(per_source[source_id] for source_id in self._source_ids)
        return ordered[0] if len(ordered) == 1 else ordered

    def _pending_updates(self):
        """Return (pending, total) subscribed PVs with nothing cached yet.

        Reading a channel that has never reported falls back to a blocking IOC
        get, so the monitor path waits until the cache is complete. Entries do
        not disappear once written, so the check latches when it is satisfied
        rather than sweeping every key on every update.
        """
        total = len(self._subscribed_keys)
        if self._cache_complete:
            return 0, total
        pending = sum(
            self._cache.get(self._name, key, Ellipsis) is Ellipsis
            for key in self._subscribed_keys
        )
        self._cache_complete = not pending
        return pending, total

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

    def _voltages_are_off(self, voltage):
        threshold = self.voltage_off_threshold
        return threshold is None or all(
            abs(actual) <= threshold for actual in self._as_tuple(voltage)
        )

    def _on_channel_update(self, update):
        timestamp = time.time()
        super()._on_channel_update(update)

        cache_key = _GROUP_VALUES.get(update.channel)
        if cache_key and not self._pending_updates()[0]:
            self._cache.put(
                self._name,
                cache_key,
                self._group_value(self._read_values(update.channel, None)),
                timestamp,
            )
        self._refresh_status(timestamp)

    def _read_values(self, channel, maxage):
        """Per-channel values for the value and status paths."""
        return {
            source_id: float(self._read_source(source_id, channel, maxage))
            for source_id in self._source_ids
        }

    def _get_values(self, channel):
        """Per-channel values straight from the IOCs, for volatile params."""
        return {
            source_id: float(self._epics.get_source_value(source_id, channel))
            for source_id in self._source_ids
        }

    def _read_flags(self, maxage):
        return {
            (source_id, channel): bool(
                int(self._read_source(source_id, channel, maxage))
            )
            for source_id in self._source_ids
            for channel in _FLAG_CHANNELS
        }

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

    def _count(self, flags, channel):
        return sum(flags[source_id, channel] for source_id in self._source_ids)

    def _fault_status(self, flags):
        alarmed = [
            source_id
            for source_id in self._source_ids
            if flags[source_id, "status_alarm"]
        ]
        if not alarmed:
            return status.OK, ""
        return status.ERROR, "; ".join(f"{source_id}: alarm" for source_id in alarmed)

    def _output_status(self, flags, voltage, setpoint):
        count = len(self._source_ids)
        requested_on = self._count(flags, "power_readback")
        channels_on = self._count(flags, "status_on")
        ramping_up = self._count(flags, "status_ramping_up")
        ramping_down = self._count(flags, "status_ramping_down")

        if not requested_on:
            still_on = channels_on or ramping_up
            if not still_on and not self._voltages_are_off(voltage):
                threshold = f"{self.voltage_off_threshold:g} {self.unit}".strip()
                return (
                    status.BUSY,
                    f"waiting for output voltages to fall to {threshold} or below",
                )
            # A ramp down is only safe to ignore when a threshold says how far
            # the voltage still has to fall.
            if still_on or (ramping_down and self.voltage_off_threshold is None):
                return status.BUSY, "waiting for outputs to disable"
            return status.DISABLED, "output disabled"
        if requested_on != count:
            return status.WARN, f"{requested_on} of {count} outputs requested on"
        if channels_on != count:
            return status.BUSY, f"{channels_on} of {count} outputs enabled"
        if ramping_up or ramping_down:
            return (
                status.BUSY,
                f"{ramping_up + ramping_down} of {count} outputs ramping",
            )
        if not self.doIsAtTarget(voltage, setpoint):
            return status.BUSY, "voltage readback has not reached target"
        return status.OK, "output enabled"

    def _compute_status(self, maxage=0):
        if maxage is None and self._cache is not None:
            pending, total = self._pending_updates()
            if pending:
                return (
                    status.UNKNOWN,
                    f"waiting for EPICS data from {pending} of {total} PVs",
                )

        flags = self._read_flags(maxage)
        voltage = self.doRead(maxage)
        setpoint = self._group_value(self._read_values("setpoint", maxage))
        hardware = super()._compute_status(maxage)

        device_status = self._output_status(flags, voltage, setpoint)

        faults = self._fault_status(flags)
        hardware_faults = worst_status(hardware, faults)
        severity = (
            device_status[0] if hardware_faults[0] == status.OK else hardware_faults[0]
        )
        details = [device_status[1]]
        details.extend(
            detail
            for candidate_status, detail in (hardware, faults)
            if candidate_status != status.OK and detail
        )
        return severity, "; ".join(details)

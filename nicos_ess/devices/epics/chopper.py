import time

from nicos.core import (
    Attach,
    Override,
    Param,
    Readable,
    Waitable,
    listof,
    oneof,
    status,
)
from nicos.devices.abstract import MappedMoveable
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    get_from_cache_or,
    status_channel,
)


class ChopperAlarms(EpicsDeviceBase, Readable):
    """
    This device handles chopper alarms.

    Every channel carries its information in the EPICS alarm fields, so the
    value callback caches the (severity, message) pair per channel and the
    combined status is the worst alarm across all channels.
    """

    parameters = {
        "pv_root": Param(
            "PV root for device", type=str, mandatory=True, userparam=False
        ),
    }
    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False),
    }

    _default_pv_prefix_attr = "pv_root"
    _primary_channel = "communication"
    _connect_channels = ("communication",)
    _epics_channels = {
        "communication": status_channel("Comm_Alrm"),
        "hardware": status_channel("HW_Alrm"),
        "interlock": status_channel("IntLock_Alrm"),
        "level": status_channel("Lvl_Alrm"),
        "position": status_channel("Pos_Alrm"),
        "power": status_channel("Pwr_Alrm"),
        "reference": status_channel("Ref_Alrm"),
        "software": status_channel("SW_Alrm"),
        "voltage": status_channel("Volt_Alrm"),
    }

    def doRead(self, maxage=0):
        return ""

    def _on_channel_update(self, update):
        ts = time.time()
        self._cache.put(
            self._name,
            self._epics.cache_key_for(update.channel),
            (update.severity, update.message),
            ts,
        )
        self._refresh_status(ts)

    def _compute_status(self, maxage=0):
        """
        Goes through all alarms in the chopper and returns the alarm encountered
        with the highest severity. All alarms are printed in the session log.
        """
        in_alarm = []
        highest_severity = status.OK
        for name in self._epics_channels:
            severity, message = self._read_channel_alarm_cached(name, maxage)
            self._log_alarm_once(name, severity, message)
            if severity == status.OK:
                continue
            if severity > highest_severity:
                highest_severity = severity
                in_alarm = [f"{name} alarm"]
            elif severity == highest_severity:
                in_alarm.append(f"{name} alarm")
        return highest_severity, ", ".join(in_alarm)

    def _read_channel_alarm_cached(self, channel, maxage=None):
        return get_from_cache_or(
            self,
            self._epics.cache_key_for(channel),
            lambda: self._epics.get_channel_alarm(channel),
            maxage=maxage,
        )


class EssChopperController(MappedMoveable):
    """Handles the status and hardware control for an ESS chopper system"""

    parameters = {
        "slit_edges": Param(
            "Slit edges of the chopper", type=listof(listof(float)), default=[]
        ),
        "resolver_offset": Param(
            "Offset of the resolver in degrees",
            type=float,
            default=0.0,
            unit="degrees",
        ),
        "tdc_offset": Param(
            "Offset of the TDC in degrees",
            type=float,
            default=0.0,
            unit="degrees",
        ),
        "spin_direction": Param(
            "Direction of rotation of the chopper",
            type=oneof("CW", "CCW"),
            default="CW",
        ),
    }

    attached_devices = {
        "state": Attach("Current state of the chopper", Readable),
        "command": Attach("Command PV of the chopper", MappedMoveable),
        "alarms": Attach("Alarms of the chopper", ChopperAlarms, optional=True),
        "speed": Attach("Speed PV of the chopper", MappedMoveable),
        "chic_conn": Attach("Status of the CHIC connection", Readable),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%s"),
        "unit": Override(mandatory=False),
        "mapping": Override(mandatory=False, userparam=False, volatile=True),
    }

    hardware_access = False
    valuetype = str

    def doRead(self, maxage=0):
        return self._attached_state.read()

    def doStart(self, target):
        if target.lower() == "stop":
            # Set the speed to zero to keep EPICS behaviour consistent.
            try:
                target_speed = self._attached_speed._inverse_mapping.get(0, "0 Hz")
                self._attached_speed.move(target_speed)
            except Exception:
                self.log.exception(
                    "Failed to set speed to 0 when stopping chopper. "
                    "Will still send stop command."
                )
        self._attached_command.move(target)

    def doStop(self):
        # Ignore - stopping the chopper is done via the move command.
        pass

    def doReset(self):
        # Ignore - resetting the chopper is done via the move command.
        pass

    def doStatus(self, maxage=0):
        if self._attached_alarms:
            stat, msg = self._attached_alarms.status(maxage)
            if stat != status.OK:
                return stat, msg
        if self._attached_chic_conn.read() != "Connected":
            return status.ERROR, "no connection to the CHIC"
        stat, msg = Waitable.doStatus(self, maxage)
        if stat != status.OK:
            return stat, msg
        return status.OK, ""

    def doReadMapping(self):
        return self._attached_command.mapping


class NewChopperAlarms(ChopperAlarms):
    """Chopper alarms for the standardized ODIN/NMX chopper setup."""

    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    _epics_channels = {
        "communication": status_channel("Comm_Alrms"),
        "hardware": status_channel("HW_Alrms"),
        "interlock": status_channel("IntLock_Alrms"),
        "level": status_channel("Lvl_Alrm"),
        "position": status_channel("Pos_Alrms"),
        "power": status_channel("Pwr_Alrms"),
        "software": status_channel("SW_Alrms"),
        "voltage": status_channel("Volt_Alrms"),
    }


class NewEssChopperController(EssChopperController):
    """Standardized ESS chopper controller for ODIN/NMX style setups."""

    attached_devices = {
        "alarms": Attach("Alarms of the chopper", NewChopperAlarms, optional=True),
    }

    parameter_overrides = {
        "mapping": Override(settable=False),
    }

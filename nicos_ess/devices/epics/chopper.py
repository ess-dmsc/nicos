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
    EpicsChannelInfo,
    EpicsChannelRole,
    EpicsDeviceBase,
    get_from_cache_or,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsManualMappedAnalogMoveable,
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

    _default_pv_root_attr = "pv_root"
    _primary_channel = "communication"
    _epics_channels = {
        "communication": EpicsChannelInfo("", "Comm_Alrm", EpicsChannelRole.STATUS),
        "hardware": EpicsChannelInfo("", "HW_Alrm", EpicsChannelRole.STATUS),
        "interlock": EpicsChannelInfo("", "IntLock_Alrm", EpicsChannelRole.STATUS),
        "level": EpicsChannelInfo("", "Lvl_Alrm", EpicsChannelRole.STATUS),
        "position": EpicsChannelInfo("", "Pos_Alrm", EpicsChannelRole.STATUS),
        "power": EpicsChannelInfo("", "Pwr_Alrm", EpicsChannelRole.STATUS),
        "reference": EpicsChannelInfo("", "Ref_Alrm", EpicsChannelRole.STATUS),
        "software": EpicsChannelInfo("", "SW_Alrm", EpicsChannelRole.STATUS),
        "voltage": EpicsChannelInfo("", "Volt_Alrm", EpicsChannelRole.STATUS),
    }

    def doPreinit(self, mode):
        self._alarm_state = {name: (status.OK, "") for name in self._epics_channels}
        EpicsDeviceBase.doPreinit(self, mode)

    def _pvs_to_connect(self):
        # Checking one PV is enough to see that the IOC is there.
        return [self._epics.pv_name_for("communication")]

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
            if severity != status.OK:
                if self._alarm_state[name] != (severity, message):
                    # Only log once
                    self._write_alarm_to_log(name, severity, message)
                if severity > highest_severity:
                    highest_severity = severity
                    in_alarm = [f"{name} alarm"]
                elif severity == highest_severity:
                    in_alarm.append(f"{name} alarm")
            self._alarm_state[name] = (severity, message)
        return highest_severity, ", ".join(in_alarm)

    def _read_channel_alarm_cached(self, channel, maxage=None):
        return get_from_cache_or(
            self,
            self._epics.cache_key_for(channel),
            lambda: self._epics.get_channel_alarm(channel),
            maxage=maxage,
        )

    def _write_alarm_to_log(self, name, severity, message):
        if severity in [status.ERROR, status.UNKNOWN]:
            self.log.error("%s (%s)", name, message)
        elif severity == status.WARN:
            self.log.warning("%s (%s)", name, message)


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


class OdinChopperController(EpicsDeviceBase, MappedMoveable):
    """Handles the status and hardware control for an ESS ODIN chopper system"""

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
        "pv_root": Param(
            "PV root for device", type=str, mandatory=True, userparam=False
        ),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%s"),
        "unit": Override(mandatory=False),
    }

    attached_devices = {
        "speed": Attach("Speed PV of the chopper", EpicsManualMappedAnalogMoveable),
    }

    valuetype = str

    _default_pv_root_attr = "pv_root"
    _primary_channel = "state"
    _epics_channels = {
        "state": EpicsChannelInfo(
            "value", "ChopState_R", EpicsChannelRole.VALUE_AND_STATUS, as_string=True
        ),
        "stop": EpicsChannelInfo(
            "", "C_Brake", EpicsChannelRole.VALUE, subscribe=False
        ),
        "start": EpicsChannelInfo(
            "", "C_RotateSync", EpicsChannelRole.VALUE, subscribe=False
        ),
        "a_start": EpicsChannelInfo(
            "", "C_RotateAsync", EpicsChannelRole.VALUE, subscribe=False
        ),
        "park": EpicsChannelInfo("", "C_Park", EpicsChannelRole.VALUE, subscribe=False),
    }

    def _after_subscribe(self, mode):
        MappedMoveable.doInit(self, mode)

    def doRead(self, maxage=0):
        return self._read_channel_cached("state", maxage=maxage)

    def doStart(self, target):
        target = target.lower()
        if target == "stop":
            self._epics.put_channel_value("stop", 1)
            # Set the speed to zero to keep EPICS behaviour consistent.
            speed_key = self._attached_speed._inverse_mapping.get(0, None)
            if speed_key is not None:
                self._attached_speed.move(speed_key)
        elif target in ("start", "a_start", "park"):
            self._epics.put_channel_value(target, 1)
        else:
            raise ValueError(f"Unknown command '{target}' for ODIN chopper")

    def doStop(self):
        # Ignore - stopping the chopper is done via the move command.
        pass

    def doReset(self):
        # Ignore - resetting the chopper is done via the move command.
        # What is the reset command for an ODIN chopper?
        pass


class NmxChopperAlarms(ChopperAlarms):
    """Chopper alarms for NMX, which uses different alarm PV suffixes."""

    _epics_channels = {
        "communication": EpicsChannelInfo("", "Comm_Alrms", EpicsChannelRole.STATUS),
        "hardware": EpicsChannelInfo("", "HW_Alrms", EpicsChannelRole.STATUS),
        "interlock": EpicsChannelInfo("", "IntLock_Alrms", EpicsChannelRole.STATUS),
        "level": EpicsChannelInfo("", "Lvl_Alrm", EpicsChannelRole.STATUS),
        "position": EpicsChannelInfo("", "Pos_Alrms", EpicsChannelRole.STATUS),
        "power": EpicsChannelInfo("", "Pwr_Alrms", EpicsChannelRole.STATUS),
        "reference": EpicsChannelInfo("", "Comm_Ref_Warn", EpicsChannelRole.STATUS),
        "software": EpicsChannelInfo("", "SW_Alrms", EpicsChannelRole.STATUS),
        "voltage": EpicsChannelInfo("", "Volt_Alrms", EpicsChannelRole.STATUS),
    }


class NmxChopperController(MappedMoveable):
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
        "alarms": Attach("Alarms of the chopper", NmxChopperAlarms, optional=True),
        "speed": Attach("Speed PV of the chopper", MappedMoveable),
        "chic_conn": Attach("Status of the CHIC connection", Readable),
    }

    parameter_overrides = {
        "fmtstr": Override(default="%s"),
        "unit": Override(mandatory=False),
        "mapping": Override(
            mandatory=False, settable=False, userparam=False, volatile=True
        ),
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

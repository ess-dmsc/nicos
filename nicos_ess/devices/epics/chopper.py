import copy
import time

from nicos import session
from nicos.core import (
    POLLER,
    Attach,
    Override,
    Param,
    Readable,
    Waitable,
    listof,
    status,
)
from nicos.devices.abstract import MappedMoveable, Moveable

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class ChopperAlarms(EpicsParameters, Readable):
    """
    This device handles chopper alarms.
    """

    parameters = {
        "pv_root": Param(
            "PV root for device", type=str, mandatory=True, userparam=False
        ),
    }
    parameter_overrides = {
        "unit": Override(mandatory=False, settable=False, volatile=False),
    }

    _alarm_state = {}
    _record_fields = {
        "communication": RecordInfo("value", "Comm_Alrm", RecordType.STATUS),
        "hardware": RecordInfo("", "HW_Alrm", RecordType.STATUS),
        "interlock": RecordInfo("", "IntLock_Alrm", RecordType.STATUS),
        "level": RecordInfo("", "Lvl_Alrm", RecordType.STATUS),
        "position": RecordInfo("", "Pos_Alrm", RecordType.STATUS),
        "power": RecordInfo("", "Pwr_Alrm", RecordType.STATUS),
        "reference": RecordInfo("", "Ref_Alrm", RecordType.STATUS),
        "software": RecordInfo("", "SW_Alrm", RecordType.STATUS),
        "voltage": RecordInfo("", "Volt_Alrm", RecordType.STATUS),
    }

    _epics_wrapper = None
    _epics_subscriptions = []

    def doPreinit(self, mode):
        self._record_fields = copy.deepcopy(self._record_fields)
        self._alarm_state = {name: (status.OK, "") for name in self._record_fields}
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check one of the PV exists
        pv = f"{self.pv_root}{self._record_fields['communication'].pv_suffix}"
        self._epics_wrapper.connect_pv(pv)

    def doInit(self, mode):
        self.log.error(f"DOINIT {session.sessiontype} {self.monitor}")
        if session.sessiontype == POLLER and self.monitor:
            self.log.error("DOINIT")
            for k, v in self._record_fields.items():
                self.log.warn(f"connecting to {k}")
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        f"{self.pv_root}{v.pv_suffix}",
                        k,
                        self._status_change_callback,
                        self._connection_change_callback,
                    )
                )

    def doRead(self, maxage=0):
        return ""

    def doStatus(self, maxage=0):
        return get_from_cache_or(self, "status", self._do_status)

    def _do_status(self):
        """
        Goes through all alarms in the chopper and returns the alarm encountered
        with the highest severity. All alarms are printed in the session log.
        """
        in_alarm = []
        highest_severity = status.OK
        for name in self._record_fields:
            severity, message = self._get_cached_status_or_ask(name)
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

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        time_stamp = time.time()
        cache_key = param
        self.log.warn(f"HELLO!!!!!! {param}, {value} {severity}, {message}")

        self._cache.put(self._name, cache_key, (severity, message), time_stamp)
        self._cache.put(self._name, "status", self._do_status(), time_stamp)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        # Only check for one PV
        if param != self._record_fields["communication"].cache_key:
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

    def _get_cached_status_or_ask(self, name):
        def _get_status_values(pv):
            return self._epics_wrapper.get_alarm_status(pv)

        pv = f"{self.pv_root}{self._record_fields[name].pv_suffix}"
        return get_from_cache_or(self, name, lambda: _get_status_values(pv))

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
    }

    attached_devices = {
        "state": Attach("Current state of the chopper", Readable),
        "command": Attach("Command PV of the chopper", MappedMoveable),
        "alarms": Attach("Alarms of the chopper", ChopperAlarms, optional=True),
        "speed": Attach("Speed PV of the chopper", Moveable),
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
            self._attached_speed.move(0)
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

import threading
import time

from nicos import session
from nicos.core import (
    Attach,
    Override,
    Param,
    status,
    CanDisable,
    pvname,
    POLLER,
)
from nicos.devices.abstract import MappedMoveable, MappedReadable, Readable

from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class PowerSupplyChannel(EpicsParameters, CanDisable, MappedReadable):
    parameters = {
        "board": Param("Power supply board"),
        "channel": Param("Power supply channel"),
        "ps_pv": Param("Power supply record PV.",
            type=pvname,
            mandatory=True,
        ),
        "voltage_monitor": Param("Voltage monitor readback value", 
            volatile=True,
            # Not sure if setting internal and userparam are making a difference.
            # Setting them anyway just for readability.
            internal=True,
            userparam=True, 
        ),
        "voltage_units": Param("Voltage monitor readback units", 
            default="V",
            type=str,
        ),
        "current_monitor": Param("Current monitor readback value", 
            volatile=True,
            internal=True,
            userparam=True,
        ),
        "current_units": Param("Current monitor readback units", 
            default="uA",
            type=str,
        ),
    }

    hardware_access = False
    valuetype = int

    def doPreinit(self, mode):
        """ From EpicsMotor class."""
        self._lock = threading.Lock()
        self._epics_subscriptions = []
        self._ps_status = (status.OK, "")
        self._record_fields = {
            "voltage_monitor": RecordInfo("", "-VMon", RecordType.VALUE),
            "current_monitor": RecordInfo("", "-IMon", RecordType.VALUE),
            "power_rb": RecordInfo("", "Pw-RB", RecordType.VALUE),
            "power": RecordInfo("", "Pw", RecordType.VALUE),
            "status_on": RecordInfo("", "-Status-ON", RecordType.VALUE),
        }
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        # Check if PV exists
        self._epics_wrapper.connect_pv(self.ps_pv + "-VMon")

    def doInit(self, mode):
        """ From EpicsMotor class."""
        if session.sessiontype == POLLER and self.monitor:
            for k, v in self._record_fields.items():
                if v.record_type in [RecordType.VALUE, RecordType.BOTH]:
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.ps_pv}{v.pv_suffix}",
                            k,
                            self._value_change_callback,
                            self._connection_change_callback,
                        )
                    )
                if v.record_type in [RecordType.STATUS, RecordType.BOTH]:
                    self._epics_subscriptions.append(
                        self._epics_wrapper.subscribe(
                            f"{self.ps_pv}{v.pv_suffix}",
                            k,
                            self._status_change_callback,
                            self._connection_change_callback,
                        )
                    )
        MappedReadable.doInit(self, mode)

    def _readRaw(self, maxage=0):
        return self._get_cached_pv_or_ask("power_rb")

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))
    
    def status_on(self):
        return bool(self._get_cached_pv_or_ask("status_on"))

    def doStatus(self, maxage=0):
        # TODO: Refactor/simplify this status method.
        # TODO: Check other status bit PVs for errors?
        channel_stat_msg = "Channel is ON" if self.status_on() else "Channel is OFF"
        
        voltage_val = self.doReadVoltage_Monitor()
        voltage_val = self.fmtstr % voltage_val if type(voltage_val) == float else None

        current_val = self.doReadCurrent_Monitor()
        current_val = self.fmtstr % current_val if type(current_val) == float else None
        
        msg = channel_stat_msg + " ({} {} / {} {})".format(
            voltage_val if voltage_val else '?', 
            self.voltage_units, 
            current_val if current_val else '?', 
            self.current_units
        )

        if not voltage_val or not current_val:
            return status.ERROR, msg        
        return status.OK, msg
    
    def doEnable(self, on):
        self._put_pv("power", 1 if on else 0)
    
    def doReadVoltage_Monitor(self):
        val = self._get_cached_pv_or_ask("voltage_monitor")
        return val
    
    def doReadCurrent_Monitor(self):
        val = self._get_cached_pv_or_ask("current_monitor")
        return val
    
    def _get_cached_pv_or_ask(self, param, as_string=False):
        """
        From EpicsMotor class.
        Gets the PV value from the cache if possible, else get it from the device.
        """
        return get_from_cache_or(
            self,
            param,
            lambda: self._get_pv(param, as_string),
        )

    def _get_pv(self, param, as_string=False):
        """From EpicsMotor class"""
        return self._epics_wrapper.get_pv_value(
            f"{self.ps_pv}{self._record_fields[param].pv_suffix}", as_string
        )
    
    def _put_pv(self, param, value):
        """From EpicsMotor class"""
        self._epics_wrapper.put_pv_value(
            f"{self.ps_pv}{self._record_fields[param].pv_suffix}", value
        )
    
    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        time_stamp = time.time()
        cache_key = self._record_fields[param].cache_key
        cache_key = param if not cache_key else cache_key
        self._cache.put(self._name, cache_key, value, time_stamp)

    def _status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        time_stamp = time.time()
        cache_key = self._record_fields[param].cache_key
        cache_key = param if not cache_key else cache_key

        if param == "value":
            self._cache.put(self._name, "value_status", (severity, message), time_stamp)
        else:
            self._cache.put(self._name, cache_key, value, time_stamp)
        self._cache.put(self._name, "status", self._do_status(), time_stamp)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
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


class PowerSupplyBank(CanDisable, MappedReadable):
    attached_devices = {
        "ps_channels": Attach("Power Supply channel", PowerSupplyChannel, multiple=True),
    }

    parameter_overrides = {
        "mapping": Override(
            mandatory=False, settable=True, userparam=False, volatile=False
        ),
    }

    hardware_access = False
    valuetype = int
    
    def _readRaw(self, maxage=0):
        """ Return 1 if there is at least one channel powered ON. Otherwise, return 0."""
        for ps_channel in self._attached_ps_channels:
            ps_channel_power_rbv = ps_channel.read()
            ps_channel_power_rbv_raw = ps_channel.mapping.get(ps_channel_power_rbv)
            if ps_channel_power_rbv_raw is None:
                return None
            if ps_channel_power_rbv_raw:
                return 1
        return 0

    def doRead(self, maxage=0):
        return self._mapReadValue(self._readRaw(maxage))
    
    def doEnable(self, on):
        """ Enable/Disable all channels of this bank."""
        for ps_channel in self._attached_ps_channels:
            ps_channel.doEnable(on)

    def doStatus(self, maxage=0):
        on_channels = 0
        num_of_channels = len(self._attached_ps_channels)
        stat = status.OK

        for ps_channel in self._attached_ps_channels:
            if ps_channel.status_on():
                on_channels += 1
        
        if on_channels == num_of_channels:
            msg = "Bank is ON (all channels are ON)"
        elif on_channels > 0:
            msg = "Bank is ON ({} of {} channels are ON)".format(
                on_channels, num_of_channels
            )
            stat = status.BUSY
        else:
            msg = "Bank is OFF (all channels are OFF)"
            stat = status.OK

        return stat, msg
            
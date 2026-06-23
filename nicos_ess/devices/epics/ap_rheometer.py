import time

import numpy

from nicos import session
from nicos.core import (
    POLLER,
    SIMULATION,
    Measurable,
    Param,
    UsageError,
    Value,
    pvname,
    status,
    usermethod,
)
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)

_CONFIG_FIELDS = {
    "interv_mode": "IntervMode",
    "osc_meas_mode": "OscIntervMeasMode",
    "visc_meas_mode": "ViscIntervMeasMode",
    "num_meas_pts": "IntervNumMeasPts",
    "duration_func": "IntervDurationFunc",
    "duration_init": "IntervDurationInit",
    "duration_final": "IntervDurationFinal",
    "stress_func": "IntervStressFunc",
    "stress_init": "IntervStressInit",
    "stress_final": "IntervStressFinal",
    "rate_func": "IntervRateFunc",
    "rate_init": "IntervRateInit",
    "rate_final": "IntervRateFinal",
    "strain_func": "IntervStrainFunc",
    "strain_init": "IntervStrainInit",
    "strain_final": "IntervStrainFinal",
    "freq_func": "IntervFreqFunc",
    "freq_init": "IntervFreqInit",
    "freq_final": "IntervFreqFinal",
    "temp_setpoint": "Temp-S",
}

_ENABLE_FIELDS = {
    "enable_osc_mode": "EnableOscMode",
    "enable_visc_mode": "EnableViscMode",
    "enable_stress": "EnableStress",
    "enable_rate": "EnableRate",
    "enable_strain": "EnableStrain",
    "enable_freq": "EnableFreq",
}

_COMMAND_FIELDS = {
    "add_interval": "IntervAdd",
    "clear_intervals": "IntervClear",
    "send_intervals": "IntervSend",
    "start": "Start",
    "stop": "Stop",
    "init_device": "InitDevice",
    "load_meas_syst": "LoadMeasSyst",
    "clear_err": "ClearErrMsg",
}

_READBACK_FIELDS = {
    "interv_raw_table": "#IntervRawTable",
    "meas_syst": "MeasSyst",
    "meas_numb": "MeasNumb-R",
    "meas_interval": "MeasInterval-R",
    "meas_state": "MeasState",
    "meas_finished": "MeasFinished",
    "meas_pt_elapsed_time": "MeasPtElapsedTime",
    "device_temp": "DeviceTemp-R",
    "gap": "Gap-R",
    "temp_mon": "Temp-Mon",
    "torque": "Torque-R",
    "force": "Force-R",
    "rot_speed": "RotSpeed-R",
    "phase_ang": "PhaseAng-R",
    "strain": "Strain-R",
    "freq": "Freq-R",
    "shear_stress": "ShearStress-R",
    "shear_rate": "ShearRate-R",
    "shear_strain": "ShearStrain-R",
    "viscosity": "Viscosity-R",
    "tot_modulus": "TotModulus-R",
    "loss_modulus": "LossModulus-R",
    "storage_modulus": "StorageModulus-R",
    "device_connected": "DeviceConnected",
    "manufacturer": "Manufacturer",
    "device_model": "DeviceModel",
    "err_msg": "ErrMsg",
}


class RheometerControl(EpicsParameters, Measurable):
    """Anton-Paar MCR 702e rheometer device."""

    parameters = {
        "pv_root": Param(
            "The PV root for the rheometer.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            key: RecordInfo(key, suffix, RecordType.VALUE)
            for fields in (
                _CONFIG_FIELDS,
                _ENABLE_FIELDS,
                _COMMAND_FIELDS,
                _READBACK_FIELDS,
            )
            for key, suffix in fields.items()
        }
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)

    def doInit(self, mode):
        if mode != SIMULATION and session.sessiontype == POLLER and self.monitor:
            for key, info in self._record_fields.items():
                if key in _COMMAND_FIELDS:  # write-only, nothing to monitor
                    continue
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        self._pv(key),
                        info.cache_key,
                        self._value_change_callback,
                        self._connection_change_callback,
                    )
                )

    def _pv(self, key):
        return f"{self.pv_root}{self._record_fields[key].pv_suffix}"

    def _get_pv(self, key, as_string=False):
        return self._epics_wrapper.get_pv_value(self._pv(key), as_string)

    def _get_cached_pv_or_ask(self, key, as_string=False):
        return get_from_cache_or(
            self,
            self._record_fields[key].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self._pv(key), as_string),
        )

    def _put_pv(self, key, value):
        self._epics_wrapper.put_pv_value(self._pv(key), value)

    def get_choices(self, key):
        """Enum choices for a combo PV, so the panel needn't hardcode lists."""
        return self._epics_wrapper.get_value_choices(self._pv(key)) or []

    @usermethod
    def set_pv(self, key, value):
        """Single trusted write entry point, restricted to known config PVs."""
        if key not in _CONFIG_FIELDS:
            raise UsageError(self, f"{key!r} is not a writable configuration PV")
        self._put_pv(key, value)

    @usermethod
    def add_interval(self):
        self._put_pv("add_interval", 1)

    @usermethod
    def clear_intervals(self):
        self._put_pv("clear_intervals", 1)

    @usermethod
    def send_intervals(self):
        self._put_pv("send_intervals", 1)

    def doStart(self):
        self._put_pv("start", 1)

    def doStop(self):
        self._put_pv("stop", 1)

    def doFinish(self):
        pass

    def doSetPreset(self, **preset):
        pass

    def presetInfo(self):
        return ()

    @usermethod
    def init_device(self):
        self._put_pv("init_device", 1)

    @usermethod
    def load_meas_syst(self):
        self._put_pv("load_meas_syst", 1)

    @usermethod
    def clear_err(self):
        self._put_pv("clear_err", 1)

    def valueInfo(self):
        return (Value(f"{self.name}.meas_numb", unit=""),)

    def doRead(self, maxage=0):
        return self._get_cached_pv_or_ask("meas_numb")

    def _is_measuring(self):
        if self.monitor:
            state = self._cache.get(self._name, "meas_state")
        else:
            state = self._get_pv("meas_state", as_string=True)
        return str(state).strip().lower() in ("1", "running")

    def _do_status(self):
        if self._mode == SIMULATION:
            return status.OK, ""
        err = self._cache.get(self._name, "err_msg") if self.monitor else None
        if err:
            return status.WARN, str(err)
        if self._is_measuring():
            return status.BUSY, "measuring"
        return status.OK, ""

    def doStatus(self, maxage=0):
        return self._do_status()

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if isinstance(value, numpy.ndarray):  # char waveform -> string
            value = "".join(chr(int(x)) for x in value)
        ts = time.time()
        self._cache.put(self._name, param, value, ts)
        if param == "meas_numb":
            self._cache.put(self._name, "value", value, ts)
        self._cache.put(self._name, "status", self._do_status(), ts)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        if param != self._record_fields["device_connected"].cache_key:
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

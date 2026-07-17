import time

from nicos.core import (
    SIMULATION,
    Measurable,
    Param,
    UsageError,
    Value,
    pvname,
    status,
    usermethod,
)
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    command_channel,
    readback_channel,
    setpoint_channel,
    status_channel,
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
    "meas_num": "MeasNumb-R",
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

# Readbacks delivered as text (char waveforms / string records).
_STRING_CHANNELS = {"interv_raw_table", "meas_syst", "manufacturer", "device_model"}


def _rheometer_channel_table():
    channels = {}
    for key, suffix in _CONFIG_FIELDS.items():
        channels[key] = setpoint_channel(suffix, "")
    for key, suffix in _ENABLE_FIELDS.items():
        channels[key] = readback_channel(suffix)
    for key, suffix in _COMMAND_FIELDS.items():
        channels[key] = command_channel(suffix)
    for key, suffix in _READBACK_FIELDS.items():
        channels[key] = readback_channel(suffix, as_string=key in _STRING_CHANNELS)
    channels["meas_num"] = readback_channel(_READBACK_FIELDS["meas_num"], primary=True)
    # meas_state and err_msg drive the NICOS status, so recompute it on every
    # update; both deliver text.
    channels["meas_state"] = status_channel(
        _READBACK_FIELDS["meas_state"], as_string=True
    )
    channels["err_msg"] = status_channel(_READBACK_FIELDS["err_msg"], as_string=True)
    channels["device_connected"] = readback_channel(
        _READBACK_FIELDS["device_connected"], affects_status=True
    )
    return channels


class RheometerControl(EpicsDeviceBase, Measurable):
    """Anton-Paar MCR 702e rheometer device."""

    parameters = {
        "pv_root": Param(
            "The PV root for the rheometer.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "temp_setpoint": Param(
            "Temperature setpoint", type=float, settable=True, volatile=True
        ),
        "meas_num": Param(
            "Measurement point number", type=float, settable=False, volatile=True
        ),
        "meas_interval": Param(
            "Active interval number", type=float, settable=False, volatile=True
        ),
        "device_temp": Param(
            "Device temperature", type=float, settable=False, volatile=True
        ),
        "temp_mon": Param("Temperature", type=float, settable=False, volatile=True),
        "gap": Param("Gap", type=float, settable=False, volatile=True),
        "torque": Param("Torque", type=float, settable=False, volatile=True),
        "force": Param("Normal force", type=float, settable=False, volatile=True),
        "rot_speed": Param(
            "Rotational speed", type=float, settable=False, volatile=True
        ),
        "phase_ang": Param("Phase angle", type=float, settable=False, volatile=True),
        "strain": Param("Strain", type=float, settable=False, volatile=True),
        "freq": Param("Frequency", type=float, settable=False, volatile=True),
        "shear_stress": Param(
            "Shear stress", type=float, settable=False, volatile=True
        ),
        "shear_rate": Param("Shear rate", type=float, settable=False, volatile=True),
        "shear_strain": Param(
            "Shear strain", type=float, settable=False, volatile=True
        ),
        "viscosity": Param("Viscosity", type=float, settable=False, volatile=True),
        "tot_modulus": Param(
            "Complex modulus |G*|", type=float, settable=False, volatile=True
        ),
        "loss_modulus": Param(
            "Loss modulus G''", type=float, settable=False, volatile=True
        ),
        "storage_modulus": Param(
            "Storage modulus G'", type=float, settable=False, volatile=True
        ),
    }

    _primary_channel = "meas_num"
    _default_pv_prefix_attr = "pv_root"
    # All channels live on the one rheometer IOC, so probing a single PV at
    # startup is enough to see that it is there.
    _connect_channels = ("device_connected",)
    _epics_channels = _rheometer_channel_table()

    def get_choices(self, key):
        """Enum choices for a combo PV, so the panel needn't hardcode lists."""
        return self._epics.get_channel_value_choices(key) or []

    @usermethod
    def set_pv(self, key, value):
        """Single trusted write entry point, restricted to known config PVs."""
        if key not in _CONFIG_FIELDS:
            raise UsageError(self, f"{key!r} is not a writable configuration PV")
        self._epics.put_channel_value(key, value)

    @usermethod
    def add_interval(self):
        """Add a measurement interval with the current interval settings."""
        self._epics.put_channel_value("add_interval", 1)

    @usermethod
    def clear_intervals(self):
        """Clear all configured measurement intervals."""
        self._epics.put_channel_value("clear_intervals", 1)

    @usermethod
    def send_intervals(self):
        """Send the configured measurement intervals to the rheometer."""
        self._epics.put_channel_value("send_intervals", 1)

    def doStart(self):
        self._epics.put_channel_value("start", 1)

    def doStop(self):
        self._epics.put_channel_value("stop", 1)

    def doFinish(self):
        pass

    def doSetPreset(self, **preset):
        pass

    def presetInfo(self):
        return ()

    @usermethod
    def init_device(self):
        """Initialize the rheometer."""
        self._epics.put_channel_value("init_device", 1)

    @usermethod
    def load_meas_syst(self):
        """Load the measuring system on the rheometer."""
        self._epics.put_channel_value("load_meas_syst", 1)

    @usermethod
    def clear_err(self):
        """Clear the error state of the rheometer."""
        self._epics.put_channel_value("clear_err", 1)

    def valueInfo(self):
        return (Value(f"{self.name}.meas_num", unit=""),)

    def _on_channel_update(self, update):
        super()._on_channel_update(update)
        if update.channel == "meas_num":
            # The measurement point number doubles as the device value.
            self._cache.put(self._name, "value", update.value, time.time())

    def _is_measuring(self, maxage=None):
        state = self._read_channel_cached("meas_state", maxage=maxage)
        return str(state).strip().lower() in ("1", "running")

    def _compute_status(self, maxage=0):
        if self._mode == SIMULATION:
            return status.OK, ""
        err = self._read_channel_cached("err_msg", maxage=maxage)
        if err:
            return status.WARN, str(err)
        if self._is_measuring(maxage):
            return status.BUSY, "measuring"
        return status.OK, ""

    def doReadTemp_Setpoint(self):
        return self._epics.get_channel_value("temp_setpoint")

    def doWriteTemp_Setpoint(self, value):
        self._epics.put_channel_value("temp_setpoint", value)

    def doReadMeas_Num(self):
        return self._epics.get_channel_value("meas_num")

    def doReadMeas_Interval(self):
        return self._epics.get_channel_value("meas_interval")

    def doReadDevice_Temp(self):
        return self._epics.get_channel_value("device_temp")

    def doReadTemp_Mon(self):
        return self._epics.get_channel_value("temp_mon")

    def doReadGap(self):
        return self._epics.get_channel_value("gap")

    def doReadTorque(self):
        return self._epics.get_channel_value("torque")

    def doReadForce(self):
        return self._epics.get_channel_value("force")

    def doReadRot_Speed(self):
        return self._epics.get_channel_value("rot_speed")

    def doReadPhase_Ang(self):
        return self._epics.get_channel_value("phase_ang")

    def doReadStrain(self):
        return self._epics.get_channel_value("strain")

    def doReadFreq(self):
        return self._epics.get_channel_value("freq")

    def doReadShear_Stress(self):
        return self._epics.get_channel_value("shear_stress")

    def doReadShear_Rate(self):
        return self._epics.get_channel_value("shear_rate")

    def doReadShear_Strain(self):
        return self._epics.get_channel_value("shear_strain")

    def doReadViscosity(self):
        return self._epics.get_channel_value("viscosity")

    def doReadTot_Modulus(self):
        return self._epics.get_channel_value("tot_modulus")

    def doReadLoss_Modulus(self):
        return self._epics.get_channel_value("loss_modulus")

    def doReadStorage_Modulus(self):
        return self._epics.get_channel_value("storage_modulus")

from collections import namedtuple

import numpy as np

from nicos.core import (
    Attach,
    Override,
    Param,
    Readable,
    Waitable,
    listof,
    pvname,
    status,
)
from nicos.devices.epics.status import SEVERITY_TO_STATUS
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    enum_readback_channel,
    enum_setpoint_channel,
    readback_channel,
    setpoint_channel,
    status_channel,
)

STAT_TO_STATUS = {
    0: "",  # NO_ALARM
    1: "READ_ALARM",
    2: "WRITE_ALARM",
    3: "HIHI_ALARM",
    4: "HIGH_ALARM",
    5: "LOLO_ALARM",
    6: "LOW_ALARM",
    7: "STATE_ALARM",
    8: "COS_ALARM",
    9: "COMM_ALARM",
    10: "TIMEOUT_ALARM",
    11: "HW_LIMIT_ALARM",
    12: "CALC_ALARM",
    13: "SCAN_ALARM",
    14: "LINK_ALARM",
    15: "SOFT_ALARM",
    16: "BAD_SUB_ALARM",
    17: "UDF_ALARM",
    18: "DISABLE_ALARM",
    19: "SIMM_ALARM",
    20: "READ_ACCESS_ALARM",
    21: "WRITE_ACCESS_ALARM",
}


EnvironmentalParameters = namedtuple(
    "EnvironmentalParameters", ["temperature", "pressure", "humidity"]
)


class MultilineController(EpicsDeviceBase, Waitable):
    parameters = {
        "pvprefix": Param(
            "Name of the record PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "polling_counter": Param(
            "Number of polling requests from IOC",
            type=int,
            settable=False,
            userparam=True,
        ),
        "front_end_splitter": Param(
            "Turn front end splitter on/off.", type=str, settable=True, internal=True
        ),
        "fes_option": Param(
            "Turn the shutter on or off when not measuring.",
            type=str,
            settable=True,
            internal=True,
        ),
        "start_measurement": Param(
            "Start of a single measurement.", type=str, settable=True, internal=True
        ),
        "alignment_process": Param(
            "Start/stop the process to align the channels.",
            type=str,
            settable=True,
            internal=True,
        ),
        "current_task": Param(
            "String value of the IOC task currently performed.",
            type=str,
            settable=False,
            internal=True,
        ),
        "measurement_lengths": Param(
            "Last measurement length array",
            type=listof(float),
            settable=False,
            internal=True,
        ),
        "align_min": Param("", type=listof(float), settable=False, internal=True),
        "align_max": Param("", type=listof(float), settable=False, internal=True),
        "measurement_errors": Param(
            "Last measurement errors",
            type=listof(int),
            settable=False,
            internal=True,
        ),
        "measurement_counter": Param(
            "Last measurement errors",
            type=listof(int),
            settable=False,
            internal=True,
        ),
        "measurement_gains": Param(
            "Gain of channels", type=listof(int), settable=True, internal=True
        ),
        "measurement_channels": Param(
            "Channels selected for measurement",
            type=listof(int),
            settable=True,
            internal=True,
        ),
        "selected_channels": Param(
            "List of selected channel flags",
            type=listof(int),
            settable=False,
            internal=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    valuetype = str

    attached_devices = {}

    _default_pv_prefix_attr = "pvprefix"
    _primary_channel = "readpv"

    _epics_channels = {
        "readpv": enum_readback_channel(
            "MeasState-R",
            cache_key="readpv",
            primary=True,
        ),
        "readpv_severity": readback_channel(
            "MeasState-R.SEVR",
            cache_key="readpv_severity",
        ),
        "front_end_splitter": enum_setpoint_channel(
            "FrontEndSplitter-S",
            refresh_status=True,
            cache_key="front_end_splitter",
            as_string=True,
        ),
        "fes_option": enum_setpoint_channel(
            "FESOption-S",
            refresh_status=True,
            cache_key="fes_option",
            as_string=True,
        ),
        "start_measurement": enum_setpoint_channel(
            "MeasStart-S",
            refresh_status=True,
            cache_key="start_measurement",
            as_string=True,
        ),
        "alignment_process": enum_setpoint_channel(
            "AlignmentStart-S",
            refresh_status=True,
            cache_key="alignment_process",
        ),
        "current_task": enum_readback_channel(
            "CurrentTask-R",
            refresh_status=True,
            cache_key="current_task",
            as_string=True,
        ),
        # 'ioc_connect': 'ConnectIOCtoServer-S',
        "num_channels": readback_channel(
            "NumChannels-R",
            refresh_status=True,
            cache_key="num_channels",
        ),
        "is_grouped": enum_readback_channel(
            "IsGrouped-R", refresh_status=True, cache_key="is_grouped", as_string=True
        ),
        "polling_counter": readback_channel(
            "PollingCounter-R",
            refresh_status=True,
            cache_key="polling_counter",
        ),
        "available_channels": readback_channel(
            "SelectedChannels-R",
            refresh_status=True,
            cache_key="selected_channels",
        ),
        "measurement_channels": setpoint_channel(
            "MeasEnableChannel-S",
            refresh_status=True,
            cache_key="measurement_channels",
        ),
        "measurement_counter": readback_channel(
            "MeasCounter-R",
            refresh_status=True,
            cache_key="measurement_counter",
        ),
        "measurement_preshots": setpoint_channel(
            "MeasPreshot-S",
            refresh_status=True,
            cache_key="measurement_preshots",
        ),
        "measurement_lengths": readback_channel(
            "DataLenLength-R",
            refresh_status=True,
            cache_key="measurement_lengths",
        ),
        "measurement_gains": readback_channel(
            "Gains-R",
            refresh_status=True,
            cache_key="measurement_gains",
        ),
        "align_min": readback_channel(
            "AlignDataMin-R",
            refresh_status=True,
            cache_key="align_min",
        ),
        "align_max": readback_channel(
            "AlignDataMax-R",
            refresh_status=True,
            cache_key="align_max",
        ),
        # channel error information
        "error_analysis": status_channel(
            "DataLenAnErr-R",
            refresh_status=True,
            cache_key="error_analysis",
        ),
        "error_interuption": status_channel(
            "DataLenBeamInt-R",
            refresh_status=True,
            cache_key="error_interuption",
        ),
        "error_temperature": status_channel(
            "DataLenTempErr-R",
            refresh_status=True,
            cache_key="error_temperature",
        ),
        "error_movement": status_channel(
            "DataLenMoveErr-R",
            refresh_status=True,
            cache_key="error_movement",
        ),
        "error_intensity": status_channel(
            "DataLenIntensErr-R",
            refresh_status=True,
            cache_key="error_intensity",
        ),
        "error_usb": status_channel(
            "DataLenUSBErr-R",
            refresh_status=True,
            cache_key="error_usb",
        ),
        "error_dll": status_channel(
            "DataLenDLLErr-R",
            refresh_status=True,
            cache_key="error_dll",
        ),
        "error_laser_speed": status_channel(
            "DataLenLSpeedErr-R",
            refresh_status=True,
            cache_key="error_laser_speed",
        ),
        "error_laser_temperature": status_channel(
            "DataLenLTempErr-R",
            refresh_status=True,
            cache_key="error_laser_temperature",
        ),
        "error_daq": status_channel(
            "DataLenDAQErr-R",
            refresh_status=True,
            cache_key="error_daq",
        ),
    }

    _error_flag_list = [
        "error_analysis",
        "error_interuption",
        "error_temperature",
        "error_movement",
        "error_intensity",
        "error_usb",
        "error_dll",
        "error_laser_speed",
        "error_laser_temperature",
        "error_daq",
    ]

    _value_codes = {
        0: "Idle",
        1: "Requested",
        2: "Measuring",
        3: "Processing",
        4: "Error",
    }

    def _get_pv_parameters(self):
        parameters = set(self._record_fields.keys())
        return parameters

    def _get_pv_name(self, pvparam):
        record_prefix = self.pvprefix
        field = self._record_fields.get(pvparam)
        if field is not None:
            return ":".join((record_prefix, field))
        return getattr(self, pvparam)

    def _compute_status(self, maxage=0):
        readpv_severity = self._read_channel_cached("readpv_severity", maxage=maxage)
        readpv_status = SEVERITY_TO_STATUS.get(readpv_severity, status.UNKNOWN)
        readpv_message = self._read_channel_cached("readpv", maxage=maxage)

        if readpv_status > status.OK:
            return readpv_status, readpv_message

        state = self.read(maxage)
        task = self.current_task
        if task == "Aligning":
            return status.BUSY, "Alignment Running"
        else:
            if state == "Idle":
                return status.OK, ""
            elif state == "Error":
                return status.ERROR, "Measurement state is error"
            else:
                return status.BUSY, ""

    @property
    def available_channels(self):
        available_channels = self.selected_channels
        return [int(chi) for chi in available_channels if chi > 0]

    def doReadSelected_Channels(self, maxage=0):
        return self._read_channel_cached("available_channels")

    def measure(self, channels=None):
        if channels is None:
            channels = self.available_channels

        for i, chi in enumerate(channels):
            # for supplied list of MeasurementChannel objects replace by channel ID
            if hasattr(chi, "channel"):
                channels[i] = chi.channel

        all_channels = self._read_channel_cached("available_channels")
        selected_channels = [1 if chi in channels else 0 for chi in all_channels]
        self.measurement_channels = selected_channels
        # TODO: Temporarily deactivated until we figure out what preshots do
        # last_preshot = self._read_channel_cached("measurement_preshots")
        # last_lengths = self._read_channel_cached("measurement_lengths")
        # new_preshot = [
        #     max(last_lengths[i], 50.0) if selected_channels[i] else max(lpi, 50.0)
        #     for i, lpi in enumerate(last_preshot)
        # ]
        # self._epics_wrapper.put_pv_value(
        #     self._get_pv_name("measurement_preshots"), new_preshot
        # )
        self._epics.put_channel_value("start_measurement", 1)

    def doReadMeasurement_Lengths(self):
        return self._read_channel_cached("measurement_lengths")

    def doReadAlign_Min(self):
        return self._read_channel_cached("align_min")

    def doReadAlign_Max(self):
        return self._read_channel_cached("align_max")

    def doReadMeasurement_Gains(self):
        return self._read_channel_cached("measurement_gains")

    def doReadMeasurement_Errors(self):
        output = np.array([0 for i in self.measurement_lengths])
        for i, error in enumerate(self._error_flag_list):
            # create bit-flag for each error
            output += 2**i * self._read_channel_cached(error)
        return output

    def doReadPolling_Counter(self):
        return self._read_channel_cached("polling_counter")

    _task_codes = {
        0: "Idle",
        1: "Polling",
        2: "Measuring",
        3: "Aligning",
        4: "Error",
    }

    def doReadCurrent_Task(self):
        value = self._read_channel_cached("current_task")
        if isinstance(value, str):
            return value
        else:
            return self._task_codes[int(value)]

    def doReadFront_End_Splitter(self):
        return self._read_channel_cached("front_end_splitter")

    def doWriteFront_End_Splitter(self, value):
        self._epics.put_channel_value("front_end_splitter", value)

    def doReadMeasurement_Counter(self):
        return self._read_channel_cached("measurement_counter")

    def doReadFes_Option(self):
        return self._read_channel_cached("fes_option")

    def doWriteFes_Option(self, value):
        self._epics.put_channel_value("fes_option", value)

    def doReadStart_Measurement(self):
        return self._read_channel_cached("start_measurement")

    def doWriteStart_Measurement(self, value):
        self._epics.put_channel_value("start_measurement", value)

    def doReadMeasurement_Channels(self):
        return self._read_channel_cached("measurement_channels")

    def doWriteMeasurement_Channels(self, value):
        self._epics.put_channel_value("measurement_channels", value)

    def doReadAlignment_Process(self):
        return self._read_channel_cached("alignment_process")

    def doWriteAlignment_Process(self, value):
        self._epics.put_channel_value("alignment_process", value)
        self._cache.invalidate(self, "status")

    def doReadIs_Grouped(self):
        return self._read_channel_cached("is_grouped")

    def doReadNum_Channels(self):
        return self._read_channel_cached("num_channels")


ML_ERROR_MESSAGES = {
    "error_analysis": "analysis error",
    "error_interuption": "beam interruption",
    "error_temperature": "temperature error",
    "error_movement": "movement tolerance error",
    "error_intensity": "intensity error",
    "error_usb": "USB connection error",
    "error_dll": "error with DLL command",
    "error_laser_speed": "error setting the laser speed",
    "error_laser_temperature": "error laser temperature",
    "error_daq": "DAQ error",
}


class MultilineChannel(Readable):
    parameters = {
        "channel": Param("Channel number", type=int, settable=False, userparam=False),
        "gain": Param("Channel gain", type=int, settable=True, userparam=True),
    }

    attached_devices = {
        "controller": Attach("Multiline Controller", MultilineController),
    }

    def doRead(self, maxage=0):
        available_channels = self._attached_controller.available_channels
        try:
            ch_idx = available_channels.index(self.channel)
        except ValueError:
            # channel not available
            return 0

        self._pollParam("gain")

        if self._attached_controller.current_task == "Aligning":
            return (
                float(
                    self._attached_controller.align_max[ch_idx]
                    - self._attached_controller.align_min[ch_idx]
                )
                / 2.0
            )
        else:
            return float(self._attached_controller.measurement_lengths[ch_idx])

    def doReadGain(self, maxage=0):
        available_channels = self._attached_controller.available_channels
        try:
            ch_idx = available_channels.index(self.channel)
        except ValueError:
            # channel not available
            return 0
        else:
            return int(self._attached_controller.measurement_gains[ch_idx])

    def doWriteGain(self, value):
        if value not in [1, 2, 4]:
            raise ValueError("Gain has to be 1,2 or 4")
        available_channels = self._attached_controller.available_channels
        try:
            ch_idx = available_channels.index(self.channel)
        except ValueError:
            # channel not available
            return
        gain_array = list(self._attached_controller.measurement_gains)
        gain_array[ch_idx] = value
        self._attached_controller.measurement_gains = gain_array

    def doStatus(self, maxage=0):
        available_channels = self._attached_controller.available_channels
        try:
            ch_idx = available_channels.index(self.channel)
        except ValueError:
            return status.ERROR, f"Channel {self.channel} not available"

        ret_stat = status.OK
        ret_msg = f"CH-{self.channel}"

        if (
            self._attached_controller.current_task == "Measuring"
            and self._attached_controller.measurement_channels[ch_idx]
        ):
            ret_stat = status.BUSY

        last_measurement = max(self._attached_controller.measurement_counter)
        if self._attached_controller.measurement_counter[ch_idx] < last_measurement:
            ret_msg += " (old data)"

        error_state = self._attached_controller.measurement_errors[ch_idx]
        for i, error in enumerate(self._attached_controller._error_flag_list):
            # create bit-flag for each error
            flag = 2**i
            if error_state & flag:
                ret_stat = status.ERROR
                ret_msg += " | " + ML_ERROR_MESSAGES[error]

        return ret_stat, ret_msg

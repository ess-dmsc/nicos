from collections import namedtuple

import numpy as np

from nicos.core import (
    Attach,
    nonemptylistof,
    Override,
    Param,
    Readable,
    pvname,
    status,
    Waitable,
)

from nicos_ess.devices.epics.pva.epics_devices import EpicsStringReadable


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


class MultilineController(EpicsStringReadable, Waitable):
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
            type=int,
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
            type=nonemptylistof(float),
            settable=False,
            internal=True,
        ),
        "align_min": Param(
            "", type=nonemptylistof(float), settable=False, internal=True
        ),
        "align_max": Param(
            "", type=nonemptylistof(float), settable=False, internal=True
        ),
        "measurement_errors": Param(
            "Last measurement errors",
            type=nonemptylistof(int),
            settable=False,
            internal=True,
        ),
        "measurement_counter": Param(
            "Last measurement errors",
            type=nonemptylistof(int),
            settable=False,
            internal=True,
        ),
        "measurement_gains": Param(
            "Gain of channels", type=nonemptylistof(int), settable=True, internal=True
        ),
        "measurement_channels": Param(
            "Channels selected for measurement",
            type=nonemptylistof(int),
            settable=True,
            internal=True,
        ),
        "selected_channels": Param(
            "List of selected channel flags",
            type=nonemptylistof(int),
            settable=False,
            internal=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(mandatory=False),
    }

    attached_devices = {}

    _record_fields = {
        "readpv": "MeasState-R",
        "front_end_splitter": "FrontEndSplitter-S",
        "fes_option": "FESOption-S",
        "start_measurement": "MeasStart-S",
        "alignment_process": "AlignmentStart-S",
        "current_task": "CurrentTask-R",
        # 'ioc_connect': 'ConnectIOCtoServer-S',
        "num_channels": "NumChannels-R",
        "is_grouped": "IsGrouped-R",
        "polling_counter": "PollingCounter-R",
        "available_channels": "SelectedChannels-R",
        "measurement_channels": "MeasEnableChannel-S",
        "measurement_counter": "MeasCounter-R",
        "measurement_preshots": "MeasPreshot-S",
        "measurement_lengths": "DataLenLength-R",
        "measurement_gains": "Gains-R",
        "align_min": "AlignDataMin-R",
        "align_max": "AlignDataMax-R",
        # channel error information
        "error_analysis": "DataLenAnErr-R",
        "error_interuption": "DataLenBeamInt-R",
        "error_temperature": "DataLenTempErr-R",
        "error_movement": "DataLenMoveErr-R",
        "error_intensity": "DataLenIntensErr-R",
        "error_usb": "DataLenUSBErr-R",
        "error_dll": "DataLenDLLErr-R",
        "error_laser_speed": "DataLenLSpeedErr-R",
        "error_laser_temperature": "DataLenLTempErr-R",
        "error_daq": "DataLenDAQErr-R",
    }

    _cache_relations = {
        "polling_counter": "polling_counter",
        "current_task": "current_task",
        "measurement_lengths": "measurement_lengths",
        "available_channels": "selected_channels",
        "align_min": "align_min",
        "align_max": "align_max",
        "measurement_gains": "measurement_gains",
        "measurement_channels": "measurement_channels",
        "measurement_counter": "measurement_counter",
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

    def doInit(self, mode):
        self.valuetype = str

    _value_codes = {
        0: "Idle",
        1: "Requested",
        2: "Measuring",
        3: "Processing",
        4: "Error",
    }

    def doRead(self, maxage=0):
        self._pollParam("current_task")
        self._pollParam("measurement_errors")
        value = EpicsStringReadable.doRead(self, maxage)
        if isinstance(value, str):
            return value
        else:
            return self._value_codes[int(value)]

    def _get_pv_parameters(self):
        parameters = set(self._record_fields.keys())
        return parameters

    def _get_pv_name(self, pvparam):
        record_prefix = getattr(self, "pvprefix")
        field = self._record_fields.get(pvparam)
        if field is not None:
            return ":".join((record_prefix, field))
        return getattr(self, pvparam)

    def doStatus(self, maxage=0):
        readpv_status, readpv_message = EpicsStringReadable.doStatus(self, maxage)

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
        return self._get_pv("available_channels")

    def measure(self, channels=None):
        if channels is None:
            channels = self.available_channels

        for i, chi in enumerate(channels):
            # for supplied list of MeasurementChannel objects replace by channel ID
            if hasattr(chi, "channel"):
                channels[i] = chi.channel

        all_channels = self._get_pv("available_channels")
        selected_channels = [1 if chi in channels else 0 for chi in all_channels]
        self.measurement_channels = selected_channels
        last_preshot = self._get_pv("measurement_preshots")
        last_lengths = self._get_pv("measurement_lengths")
        new_preshot = [
            max(last_lengths[i], 50.0) if selected_channels[i] else max(lpi, 50.0)
            for i, lpi in enumerate(last_preshot)
        ]
        self._put_pv("measurement_preshots", new_preshot, wait=True)
        self._put_pv("start_measurement", 1, wait=True)

    def doReadMeasurement_Lengths(self):
        return self._get_pv("measurement_lengths")

    def doReadAlign_Min(self):
        return self._get_pv("align_min")

    def doReadAlign_Max(self):
        return self._get_pv("align_max")

    def doReadMeasurement_Gains(self):
        return self._get_pv("measurement_gains")

    def doReadMeasurement_Errors(self):
        output = np.array([0 for i in self.measurement_lengths])
        for i, error in enumerate(self._error_flag_list):
            # create bit-flag for each error
            output += 2**i * self._get_pv(error)
        return output

    def doReadPolling_Counter(self):
        return self._get_pv("polling_counter")

    _task_codes = {
        0: "Idle",
        1: "Polling",
        2: "Measuring",
        3: "Aligning",
        4: "Error",
    }

    def doReadCurrent_Task(self):
        value = self._get_pv("current_task", as_string=True)
        if isinstance(value, str):
            return value
        else:
            return self._task_codes[int(value)]

    def doReadFront_End_Splitter(self):
        return self._get_pv("front_end_splitter", as_string=True)

    def doWriteFront_End_Splitter(self, value):
        self._put_pv("front_end_splitter", value, wait=True)

    def doReadMeasurement_Counter(self):
        return self._get_pv("measurement_counter")

    def doReadFes_Option(self):
        return self._get_pv("fes_option", as_string=True)

    def doWriteFes_Option(self, value):
        self._put_pv("fes_option", value, wait=True)

    def doReadStart_Measurement(self):
        return self._get_pv("start_measurement", as_string=True)

    def doWriteStart_Measurement(self, value):
        self._put_pv("start_measurement", value, wait=True)

    def doReadMeasurement_Channels(self):
        return self._get_pv("measurement_channels")

    def doWriteMeasurement_Channels(self, value):
        self._put_pv("measurement_channels", value, wait=True)

    def doReadAlignment_Process(self):
        return self._get_pv("alignment_process")

    def doWriteAlignment_Process(self, value):
        self._put_pv("alignment_process", value, wait=True)
        self._cache.invalidate(self, "status")

    def doReadIs_Grouped(self):
        return self._get_pv("is_grouped", as_string=True)

    def doReadNum_Channels(self):
        return self._get_pv("num_channels")


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
        "controller": Attach("Multline Controller", MultilineController),
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

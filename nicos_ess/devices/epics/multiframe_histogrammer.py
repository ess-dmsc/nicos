import time

import numpy as np

from nicos import session
from nicos.core import (
    LIVE,
    POLLER,
    SIMULATION,
    ArrayDesc,
    InvalidValueError,
    Override,
    Param,
    Readable,
    Value,
    anytype,
    dictof,
    floatrange,
    listof,
    multiStatus,
    oneof,
    pvname,
    status,
)
from nicos.devices.epics.pva import EpicsDevice
from nicos.devices.epics.status import SEVERITY_TO_STATUS, STAT_TO_STATUS
from nicos.devices.generic import ImageChannelMixin, PassiveChannel
from nicos.utils import byteBuffer
from nicos_ess.devices.epics.pva import EpicsReadable
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    RecordInfo,
    RecordType,
    create_wrapper,
    get_from_cache_or,
)


class MultiFrameHistogrammer(
    ImageChannelMixin, EpicsParameters, Readable, PassiveChannel
):
    """
    Device that controls and acquires data from a multiframe-histogrammer.
    """

    parameters = {
        "pv_root": Param(
            "EPICS prefix",
            type=pvname,
            mandatory=True,
        ),
        "iscontroller": Param(
            "If this channel is an active controller",
            type=bool,
            settable=True,
            default=True,
        ),
        "source_name_input": Param(
            "Source name for input.",
            type=str,
            default="no_source",
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "source_name_output": Param(
            "Source name for output.",
            type=str,
            default="no_source",
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "topic_input": Param(
            "Kafka topic name for input.",
            type=str,
            default="no_topic",
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "topic_output": Param(
            "Kafka topic name for output.",
            type=str,
            default="no_topic",
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "num_histograms": Param(
            "Boxcar width for spectrum.",
            type=int,
            default=1,
            volatile=True,
            settable=True,
            userparam=True,
        ),
        "started": Param(
            "Whether a collection is in progress",
            type=bool,
            settable=True,
            default=False,
            internal=True,
        ),
    }

    _plot_update_delay = 0.25

    def doPreinit(self, mode):
        self._record_fields = {
            "readpv": RecordInfo("value", "", RecordType.BOTH),
            "frame_time": RecordInfo("", "frame_time", RecordType.VALUE),
            "source_name_input": RecordInfo("", "source_name_input", RecordType.VALUE),
            "source_name_output": RecordInfo(
                "", "source_name_output", RecordType.VALUE
            ),
            "topic_input": RecordInfo("", "topic_input", RecordType.VALUE),
            "topic_output": RecordInfo("", "topic_output", RecordType.VALUE),
            "num_histograms": RecordInfo("", "num_histograms", RecordType.VALUE),
        }

        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)
        self._epics_wrapper.connect_pv(self.readpv)
        self.started = False
        self._current_status = (status.OK, "")
        self._signal_array = []
        self._frame_time_array = []
        self.readresult = [0]
        self._last_update = 0

    def doInit(self, mode):
        if session.sessiontype == POLLER and self.monitor:
            for k, v in self._record_fields.items():
                self._epics_subscriptions.append(
                    self._epics_wrapper.subscribe(
                        f"{self.pv_root}{v.pv_suffix}",
                        k,
                        self._status_change_callback,
                        self._connection_change_callback,
                    )
                )

    def doPrepare(self):
        self._signal_array = []
        self._frame_time_array = []
        self.readresult = [0]
        self._last_update = 0
        self.started = False
        self._update_status(status.OK, "")

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def doReadArray(self, quality):
        return self._signal_array

    def status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        self.log.warn("Status change callback called for %s", name)
        if param == "readpv":
            self._signal_array = value
            self.readresult = np.sum(value, axis=0)
            if time.monotonic() >= self._last_update + self._plot_update_delay:
                self.putResult(LIVE, value)
                self._last_update = time.monotonic()
        elif param == "frame_time":
            self._frame_time_array = value

        EpicsReadable.status_change_callback(
            self, name, param, value, units, limits, severity, message, **kwargs
        )

    def value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        self.log.warn("Value change callback called for %s", name)
        EpicsReadable.value_change_callback(
            self, name, param, value, units, limits, severity, message, **kwargs
        )

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)

    def arrayInfo(self):
        return ArrayDesc(
            self.name,
            shape=self._signal_array.shape,
            dtype=self._signal_array.dtype,
        )

    def putResult(self, quality, data):
        databuffer = [byteBuffer(np.ascontiguousarray(data))]
        datadesc = [
            dict(
                dtype=data.dtype.str,
                shape=data.shape,
                labels={
                    "x": {
                        "define": "array",
                        "index": 0,
                        "dtype": "<f4",
                    },
                },
                plotcount=1,
            )
        ]
        if databuffer:
            parameters = dict(
                uid=0,
                time=time.time(),
                det=self.name,
                tag=LIVE,
                datadescs=datadesc,
            )
            self._frame_time_array = self._get_pv("frame_time")
            labelbuffers = [
                byteBuffer(
                    np.ascontiguousarray(
                        np.array(self._frame_time_array).astype(np.float32)
                    )
                )
            ]
            session.updateLiveData(parameters, databuffer, labelbuffers)

    def _get_pv_parameters(self):
        return set(self._record_fields.keys())

    def _get_pv_name(self, pvparam):
        pv_record_info = self._record_fields.get(pvparam)
        if pv_record_info:
            pv_name = pv_record_info.pv_suffix
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def doStart(self):
        self.readresult = [0]
        self.started = True

    def doFinish(self):
        self.started = False

    def doStop(self):
        self.started = False

    def doStatus(self, maxage=0):
        if self.started:
            return status.BUSY, "counting"
        return status.OK, ""

    def _get_pv(self, pvparam):
        return get_from_cache_or(
            self,
            self._record_fields[pvparam].cache_key,
            lambda: self._epics_wrapper.get_pv_value(self._get_pv_name(pvparam)),
        )

    def _put_pv(self, pvparam, value):
        self._epics_wrapper.put_pv_value(self._get_pv_name(pvparam), value)

    def doReadSource_Name_Input(self):
        return self._get_pv("source_name_input")

    def doWriteSource_Name_Input(self, value):
        self._put_pv("source_name_input", value)

    def doReadSource_Name_Output(self):
        return self._get_pv("source_name_output")

    def doWriteSource_Name_Output(self, value):
        self._put_pv("source_name_output", value)

    def doReadTopic_Input(self):
        return self._get_pv("topic_input")

    def doWriteTopic_Input(self, value):
        self._put_pv("topic_input", value)

    def doReadTopic_Output(self):
        return self._get_pv("topic_output")

    def doWriteTopic_Output(self, value):
        self._put_pv("topic_output", value)

    def doReadNum_Histograms(self):
        return self._get_pv("num_histograms")

    def doWriteNum_Histograms(self, value):
        self._put_pv("num_histograms", value)

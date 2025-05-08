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
from nicos.devices.epics.pva import EpicsReadable
from nicos.devices.epics.status import SEVERITY_TO_STATUS, STAT_TO_STATUS
from nicos.devices.generic import ImageChannelMixin, PassiveChannel
from nicos.utils import byteBuffer


class MultiFrameHistogrammer(ImageChannelMixin, EpicsReadable, PassiveChannel):
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

    _plot_update_delay = 1.0

    def doPreinit(self, mode):
        self._record_fields = {
            "readpv": "signal",
            "frame_time": "frame_time",
            "source_name_input": "source_name_input",
            "source_name_output": "source_name_output",
            "topic_input": "topic_input",
            "topic_output": "topic_output",
            "num_histograms": "num_histograms",
        }
        self._current_status = (status.OK, "")
        self._signal_array = np.array([])
        self._frame_time_array = np.array([])
        self._last_update = 0
        EpicsReadable.doPreinit(self, mode)
        if session.sessiontype != POLLER:
            self.readresult = [0]
            self.started = False

    def doPrepare(self):
        self._signal_array = np.array([])
        self._frame_time_array = np.array([])
        self.readresult = [0]
        self._last_update = 0
        self.started = False
        self._update_status(status.OK, "")

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def doReadArray(self, quality):
        return self._signal_array

    def _register_pv_callbacks(self):
        self._epics_subscriptions = []
        value_pvs = list(self._cache_relations.keys())
        status_pvs = self._get_status_parameters()
        if session.sessiontype == POLLER:
            self._subscribe_params(value_pvs, self.value_change_callback)
        else:
            self._subscribe_params(status_pvs or value_pvs, self.status_change_callback)

    def value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        cache_key = self._get_cache_relation(param)
        if cache_key:
            if param == "readpv":
                self._cache.put(self._name, cache_key, self.readresult, time.time())
                self._cache.put(self._name, "unit", units, time.time())
            else:
                self._cache.put(self._name, cache_key, value, time.time())

    def status_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        if (
            param == "readpv"
            and time.monotonic() < self._last_update + self._plot_update_delay
        ):
            return
        elif param == "readpv":
            self._signal_array = value
            self.readresult = [np.sum(value, axis=0)]
            self.update_arraydesc()
            self.log.warn(f"Trying to put {self.readresult}")
            self.putResult(LIVE, value)
            self._last_update = time.monotonic()

        current_status = self.doStatus()
        self._cache.put(self._name, "status", current_status, time.time())

    def valueInfo(self):
        return (Value(self.name, unit=self.unit, fmtstr=self.fmtstr),)

    def arrayInfo(self):
        return self.update_arraydesc(self)

    def update_arraydesc(self):
        self.arraydesc = ArrayDesc(
            self.name, shape=self._signal_array.shape, dtype=np.int32
        )
        return self.arraydesc

    def putResult(self, quality, data):
        self.log.warn(f"Trying to put data")
        self._frame_time_array = self._get_pv("frame_time").astype(np.float64)
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
                plot_type="hist-1d",
                label_shape=tuple([len(self._frame_time_array)]),
                label_dtypes=tuple([self._frame_time_array.dtype.str]),
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
            labelbuffers = [byteBuffer(np.ascontiguousarray(self._frame_time_array))]
            session.updateLiveData(parameters, databuffer, labelbuffers)

    def _get_pv_parameters(self):
        return set(self._record_fields.keys())

    def _get_pv_name(self, pvparam):
        pv_name = self._record_fields.get(pvparam)
        if pv_name:
            return self.pv_root + pv_name
        return getattr(self, pvparam)

    def doRead(self, maxage=0):
        return self.readresult

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

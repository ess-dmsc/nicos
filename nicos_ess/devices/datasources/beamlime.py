import json
import time

import numpy as np
from streaming_data_types import deserialise_da00
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    LIVE,
    POLLER,
    SIMULATION,
    ArrayDesc,
    Override,
    Param,
    host,
    listof,
    multiStatus,
    status,
    tupleof,
)
from nicos.devices.generic import CounterChannelMixin, Detector, PassiveChannel
from nicos.utils import byteBuffer
from nicos_ess.devices.kafka.consumer import KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer


class DataChannel(CounterChannelMixin, PassiveChannel):
    # class DataChannel(Readable, PassiveChannel):
    """
    Channel device that stores histogram/image data (1D or 2D)
    and pushes it to NICOS via putResult(). The main (master)
    BeamLimeCollector receives Kafka da00 data and routes it here.
    """

    parameters = {
        "source_name": Param(
            "Identifier source on multiplexed topics",
            type=str,
            default="",
            userparam=True,
            settable=True,
        ),
        "toa_range": Param(
            "Time-of-arrival range",
            type=tupleof(int, int),
            default=(0, 100_000_000),
            userparam=True,
            settable=True,
        ),
        "num_bins": Param(
            "Number of bins (for 1D) or binning param (for 2D)",
            type=int,
            default=100,
            userparam=True,
            settable=True,
        ),
        "sliding_window": Param(
            "Sliding window size in seconds",
            type=float,
            default=10.0,
            userparam=True,
            settable=True,
        ),
        "roi_active": Param(
            "Region of interest active",
            type=bool,
            default=False,
            userparam=True,
            settable=True,
        ),
        "roi": Param(
            "Region of interest, coordinates with winding order by index",
            type=list,
            default=[],
            userparam=True,
            settable=True,
        ),
        "last_clear": Param(
            "Last clear time",
            type=int,
            default=0,
            userparam=True,
            settable=True,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "curvalue": Param(
            "Store the current device value",
            internal=True,
            type=int,
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="events", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    data_structure = {}
    _current_status = (status.UNKNOWN, "")
    _signal_data = np.array([])
    _signal_data_sum = 0
    _collector = None

    def doPreinit(self, mode):
        self._current_status = (status.OK, "")
        self._signal_data = np.array([])
        self._signal_data_sum = 0
        if mode == SIMULATION:
            return
        self._update_status(status.OK, "")

    def _update_status(self, new_status, message):
        self._current_status = (new_status, message)
        self._cache.put(self._name, "status", self._current_status, time.time())

    def doRead(self, maxage=0):
        return self.curvalue

    def doReadArray(self, quality):
        return self._signal_data

    def arrayInfo(self):
        return self.update_arraydesc()

    def update_arraydesc(self):
        if self.data_structure:
            return ArrayDesc(
                self.name, shape=self.data_structure["signal_shape"], dtype=np.int32
            )
        else:
            return ArrayDesc(self.name, shape=(), dtype=np.int32)

    def doStatus(self, maxage=0):
        return self._current_status

    def update_data(self, message, timestamp):
        try:
            if message.source_name != self.source_name:
                self.log.warn(
                    f"Source name mismatch for device {self.name}, "
                    f"message from {message.source_name} instead "
                    f"of {self.source_name}"
                )
                return

            self.data_structure.clear()
            variables = message.data
            self._parse_new_data(variables)
            self.update_arraydesc()
            self._signal_data = self.data_structure["signal"]
            self._signal_data_sum = (
                int(self._signal_data.sum()) if self._signal_data.size else 0
            )
            self.curvalue = self._signal_data_sum

            self.poll()

            if len(self.arrayInfo().shape) == 1:
                plot_type = "hist-1d"
            elif len(self.arrayInfo().shape) == 2:
                plot_type = "hist-2d"
            else:
                self.log.warn(f"Unknown plot type for device {self.name}")
                return

            if self.data_structure:
                self.putResult(
                    1,
                    self.get_plot_data(),
                    timestamp,
                    message.source_name,
                    plot_type,
                    # self.data_structure["plot_type"],
                )
        except Exception as e:
            print(f"Could not update data for {self.name}: {e}")

    def _parse_new_data(self, variables):
        if not variables:
            return

        for var in variables:
            if var.name == "signal":
                self.data_structure["signal"] = var.data
                self.data_structure["signal_axes"] = var.axes
                self.data_structure["signal_shape"] = var.shape
                self.data_structure["plot_type"] = var.label
                variables.remove(var)

        for var in variables:
            var_axes = var.axes
            if not any([ax in var_axes for ax in self.data_structure["signal_axes"]]):
                continue
            if len(var_axes) != 1:
                continue

            var_axis = str(var_axes[0])

            self.data_structure[var_axis] = var.data
            self.data_structure[var_axis + "_axes"] = var.axes
            self.data_structure[var_axis + "_shape"] = var.shape

        if len(self.data_structure["signal_axes"]):
            # create signal axes based on the shape of the signal with arange
            for i, axis_name in enumerate(self.data_structure["signal_axes"]):
                exists = self.data_structure.get(axis_name, None)
                if exists is not None:
                    continue
                arr = np.arange(self.data_structure["signal_shape"][i])
                # store the numeric array in the data_structure under the string key
                self.data_structure[axis_name] = arr
                self.data_structure[axis_name + "_shape"] = arr.shape

    def get_plot_data(self):
        """
        Returns data in the order [x, y, z] for plotting. Like [axes_1, axes_2, signal].
        """
        try:
            axes_to_plot_against = self.data_structure["signal_axes"]
            plot_data = [self.data_structure[axis] for axis in axes_to_plot_against]
            plot_data.append(self.data_structure["signal"])
            return plot_data
        except KeyError:
            return None

    def putResult(self, quality, data, timestamp, source_name, plot_type=None):
        signal_data = data.pop(-1)
        databuffer = [byteBuffer(np.ascontiguousarray(signal_data))]
        datadesc = [
            dict(
                dtype=signal_data.dtype.str,
                shape=signal_data.shape,
                labels={
                    "x": {"define": "classic"},
                    "y": {"define": "classic"},
                },
                plotcount=1,
                plot_type=plot_type,
                label_shape=tuple([len(label_data) for label_data in data]),
                label_dtypes=tuple([label_data.dtype.str for label_data in data]),
            )
        ]
        if databuffer:
            parameters = dict(
                uid=0,
                time=timestamp,
                det=source_name,
                tag=LIVE,
                datadescs=datadesc,
            )
            data = np.ascontiguousarray(np.concatenate(data), dtype=np.float64)
            labelbuffers = [byteBuffer(data)]
            session.updateLiveData(parameters, databuffer, labelbuffers)

    def _send_command_to_collector(self, param_name, value):
        if self._collector:
            self._collector.send_command(param_name, value)

    def doStart(self):
        self._update_status(status.BUSY, "Started acquisition")
        self.last_clear = time.time_ns()
        message = json.dumps({"value": self.last_clear, "unit": "ns"}).encode("utf-8")
        self._send_command_to_collector("start_time", message)

    def doStop(self):
        self._update_status(status.OK, "Stopped acquisition")

    def doWriteNum_Bins(self, value):
        self._send_command_to_collector("num_bins", value)

    def doWriteSliding_Window(self, value):
        self._send_command_to_collector("sliding_window", value)

    def doWriteToa_Range(self, value):
        self._send_command_to_collector("toa_range", value)

    def doWriteRoi_Active(self, value):
        self._send_command_to_collector("roi_active", value)

    def doWriteRoi(self, value):
        self._send_command_to_collector("roi", value)


class BeamLimeCollector(Detector):
    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "topic": Param(
            "Kafka topic(s) where messages are written",
            type=listof(str),
            settable=False,
            preinit=True,
            mandatory=True,
            userparam=False,
        ),
        "command_topic": Param(
            "Kafka topic to which we may send config commands",
            type=str,
            default="",
            userparam=False,
            settable=False,
        ),
        "schema": Param(
            "Schema we expect for the incoming data (e.g. da00)",
            type=str,
            default="da00",
            userparam=False,
            settable=False,
        ),
    }

    _kafka_subscriber = None

    def doPreinit(self, mode):
        Detector.doPreinit(self, mode)
        if mode == SIMULATION:
            return

        if session.sessiontype != POLLER:
            for channel in self._channels:
                channel._collector = self

            self._kafka_subscriber = KafkaSubscriber(self.brokers)
            self._kafka_subscriber.subscribe(
                self.topic,
                self.new_messages_callback,
                self.no_messages_callback,
            )

            self._kafka_producer = KafkaProducer.create(self.brokers)

        self._collectControllers()
        self._update_status(status.WARN, "Initializing BeamLimeCollector...")

    def _update_status(self, new_status, msg=""):
        self._cache.put(self, "status", (new_status, msg), time.time())

    def doRead(self, maxage=0):
        return [data for channel in self._channels for data in channel.read(maxage)]

    def doStatus(self, maxage=0):
        return multiStatus(self._channels, maxage)

    def send_command(self, param_name, message):
        def cb(err, msg):
            if err:
                self.log.warn(f"Error sending command: {err}")
            else:
                self.log.debug(f"Command sent: {msg}")

        if self._kafka_producer:
            self._kafka_producer.produce(
                self.command_topic,
                message=message,
                key=param_name,
                on_delivery_callback=cb,
            )
        else:
            self.log.warn("No producer available to send command")

    def new_messages_callback(self, messages):
        for timestamp, message in messages:
            try:
                if get_schema(message) != self.schema:
                    continue
                da00_msg = deserialise_da00(message)
                src = da00_msg.source_name

                matched_channel = None
                for ch in self._channels:
                    if getattr(ch, "source_name", "") == src:
                        matched_channel = ch
                        break

                if matched_channel:
                    matched_channel.update_data(da00_msg, timestamp)

            except Exception as e:
                self.log.warn(f"Could not decode or route da00 message: {e}")

    def no_messages_callback(self):
        pass

    def doShutdown(self):
        self._kafka_subscriber.close()

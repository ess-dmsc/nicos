import json
import threading
import time

import numpy as np
from streaming_data_types import deserialise_hs00, deserialise_hs01
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    ArrayDesc,
    Override,
    Param,
    Value,
    floatrange,
    host,
    listof,
    oneof,
    status,
    tupleof,
)
from nicos.core.constants import MASTER, POLLER, SIMULATION
from nicos.devices.generic import Detector, ImageChannelMixin, PassiveChannel
from nicos.utils import createThread
from nicos_ess.devices.kafka.consumer import KafkaConsumer, KafkaSubscriber
from nicos_ess.devices.kafka.producer import KafkaProducer
from nicos_ess.devices.kafka.status_handler import (
    DISCONNECTED_STATE,
    KafkaStatusHandler,
)


class Hist1dTof:
    name = "hist1d"

    @classmethod
    def get_array_description(cls, name, num_bins, **ignored):
        return ArrayDesc(name, shape=(num_bins,), dtype=np.float64)

    @classmethod
    def get_zeroes(cls, num_bins, **ignored):
        return cls.transform_data(np.zeros(shape=(num_bins,), dtype=np.float64))

    @classmethod
    def transform_data(cls, data, rotation=None):
        return data

    @classmethod
    def get_info(cls, name, num_bins, **ignored):
        return [(f"{name} bins", num_bins, str(num_bins), "", "general")]


class Hist2dTof:
    name = "hist2d"

    @classmethod
    def get_array_description(cls, name, num_bins, **ignored):
        return ArrayDesc(name, shape=(num_bins, num_bins), dtype=np.float64)

    @classmethod
    def get_zeroes(cls, num_bins, **ignored):
        return cls.transform_data(
            np.zeros(shape=(num_bins, num_bins), dtype=np.float64)
        )

    @classmethod
    def transform_data(cls, data, rotation=None):
        # For the ESS detector orientation, pixel 0 is at top-left
        if rotation:
            return np.rot90(data, k=rotation // 90)
        return data

    @classmethod
    def get_info(cls, name, num_bins, **ignored):
        return [
            (
                f"{name} bins",
                (num_bins, num_bins),
                str((num_bins, num_bins)),
                "",
                "general",
            )
        ]


class Hist2dDet:
    name = "dethist"

    @classmethod
    def get_array_description(cls, name, det_width, det_height, **ignored):
        return ArrayDesc(name, shape=(det_width, det_height), dtype=np.float64)

    @classmethod
    def get_zeroes(cls, det_width, det_height, **ignored):
        return cls.transform_data(
            np.zeros(shape=(det_width, det_height), dtype=np.float64)
        )

    @classmethod
    def transform_data(cls, data, rotation=None):
        # For the ESS detector orientation, pixel 0 is at top-left
        if rotation:
            return np.rot90(data, k=rotation // 90)
        return data

    @classmethod
    def get_info(cls, name, det_width, det_height, **ignored):
        return [
            (f"{name} width", det_width, str(det_width), "", "general"),
            (f"{name} height", det_height, str(det_height), "", "general"),
        ]


class Hist2dRoi:
    name = "roihist"

    @classmethod
    def get_array_description(cls, name, det_width, left_edges, **ignored):
        return ArrayDesc(name, shape=(det_width, left_edges), dtype=np.float64)

    @classmethod
    def get_zeroes(cls, det_width, left_edges, **ignored):
        return cls.transform_data(
            np.zeros(shape=(det_width, left_edges), dtype=np.float64)
        )

    @classmethod
    def transform_data(cls, data, rotation=None):
        # For the ESS detector orientation, pixel 0 is at top-left
        if rotation:
            return np.rot90(data, k=rotation // 90)
        return data

    @classmethod
    def get_info(cls, name, det_width, left_edges, **ignored):
        height = len(left_edges)
        return [
            (f"{name} width", det_width, str(det_width), "", "general"),
            (f"{name} height", height, str(height), "", "general"),
        ]


hist_type_by_name = {
    "1-D TOF": Hist1dTof,
    "2-D TOF": Hist2dTof,
    "2-D DET": Hist2dDet,
    "2-D ROI": Hist2dRoi,
}

deserialiser_by_schema = {
    "hs00": deserialise_hs00,
    "hs01": deserialise_hs01,
}

input_schemas = ("ev42", "ev44", "da00")


def decode_histogram(message):
    deserialiser = deserialiser_by_schema.get(get_schema(message))
    if not deserialiser:
        return None
    hist = deserialiser(message)
    return hist, json.loads(hist["info"])


class JustBinItImage(ImageChannelMixin, PassiveChannel):
    arraydesc = ArrayDesc("", shape=(0,), dtype=np.float64)

    parameters = {
        "brokers": Param(
            "List of kafka brokers to connect to",
            type=listof(host(defaultport=9092)),
            mandatory=True,
            preinit=True,
            userparam=False,
        ),
        "hist_topic": Param(
            "The topic to listen on for the histogram data",
            type=str,
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "data_topic": Param(
            "The topic to listen on for the event data",
            type=str,
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "hist_type": Param(
            "The number of dimensions to histogram in",
            type=oneof(*hist_type_by_name.keys()),
            default="1-D TOF",
            userparam=True,
            settable=True,
        ),
        "tof_range": Param(
            "The time-of-flight range to histogram",
            type=tupleof(int, int),
            default=(0, 100000000),
            userparam=True,
            settable=True,
        ),
        "det_range": Param(
            "The detector range to histogram over",
            type=tupleof(int, int),
            default=(1, 100),
            userparam=True,
            settable=True,
        ),
        "det_width": Param(
            "The width in pixels of the detector",
            type=int,
            default=10,
            userparam=True,
            settable=True,
        ),
        "det_height": Param(
            "The height in pixels of the detector",
            type=int,
            default=10,
            userparam=True,
            settable=True,
        ),
        "num_bins": Param(
            "The number of bins to histogram into",
            type=int,
            default=50,
            userparam=True,
            settable=True,
        ),
        "left_edges": Param(
            "The left edges for a ROI histogram",
            type=listof(int),
            default=[],
            userparam=True,
            settable=True,
        ),
        "source": Param(
            "Identifier source on multiplexed topics",
            type=str,
            default="",
            userparam=True,
            settable=True,
        ),
        "input_schema": Param(
            "Optional input schema override for this image channel",
            type=oneof("", *input_schemas),
            default="",
            userparam=False,
            settable=True,
        ),
        "rotation": Param(
            "Rotation angle to apply to the image",
            type=oneof(0, 90, 180, 270),
            default=90,
            userparam=True,
            settable=True,
        ),
        "event_rate": Param(
            "The neutron event rate",
            type=float,
            unit="counts/s",
            default=0.0,
            userparam=False,
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="events", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    def doPreinit(self, mode):
        self._unique_id = None
        self._current_status = (status.OK, "")
        self._finished = threading.Event()
        self._last_state = None
        if mode == SIMULATION:
            return
        self._update_status(status.OK, "")

    def doInit(self, mode):
        self._hist_sum = 0
        self._setROParam("event_rate", 0.0)
        self._zero_data()

    def _zero_data(self):
        self.arraydesc = hist_type_by_name[self.hist_type].get_array_description(
            **self._params
        )
        self._hist_data = hist_type_by_name[self.hist_type].get_zeroes(**self._params)

    def arrayInfo(self):
        return self.arraydesc

    def doPrepare(self):
        self._unique_id = None
        self._zero_data()
        self._hist_edges = np.array([])
        self._hist_sum = 0
        self._finished.clear()
        self._last_state = None
        self._setROParam("event_rate", 0.0)
        self._update_status(status.OK, "")

    @property
    def finished(self):
        return self._finished.is_set()

    def wait_finished(self, timeout):
        return self._finished.wait(timeout)

    def on_histogram(self, hist, info):
        if not self._unique_id or info.get("id") != self._unique_id:
            return
        state = info.get("state")
        self._hist_data = hist_type_by_name[self.hist_type].transform_data(
            hist["data"], rotation=self.rotation
        )
        self._hist_sum = self._hist_data.sum()
        self._hist_edges = hist["dim_metadata"][0]["bin_boundaries"]
        rate = info.get("rate")
        if rate is not None and self._mode == MASTER:
            self._setROParam("event_rate", rate)
        if state == self._last_state:
            return
        self._last_state = state
        if state == "ERROR":
            # the histogram process has ended, no FINISHED will follow
            error_msg = info.get("error_message", "unknown error")
            self.log.warning("just-bin-it failed: %s", error_msg)
            self._update_status(status.WARN, error_msg)
            self._finished.set()
        elif state == "FINISHED":
            self._update_status(status.OK, "")
            self._finished.set()
        else:
            self._update_status(status.BUSY, "Counting")

    def _update_status(self, new_status, message):
        self._current_status = new_status, message
        self._cache.put(self._name, "status", self._current_status, time.time())

    def doRead(self, maxage=0):
        return [self._hist_sum]

    def doReadArray(self, quality):
        return self._hist_data

    def valueInfo(self):
        return (Value(self.name, fmtstr="%d"),)

    def doStart(self):
        self._update_status(status.BUSY, "Waiting to start...")

    def doFinish(self):
        self._unique_id = None
        if not self._finished.is_set():
            self._update_status(status.OK, "")

    def doStop(self):
        self._unique_id = None
        self._update_status(status.OK, "")

    def doStatus(self, maxage=0):
        return self._current_status

    def get_configuration(self, unique_id):
        self._unique_id = unique_id

        config = {
            "type": hist_type_by_name[self.hist_type].name,
            "data_brokers": self.brokers,
            "data_topics": [self.data_topic],
            "tof_range": list(self.tof_range),
            "det_range": list(self.det_range),
            "num_bins": self.num_bins,
            "width": self.det_width,
            "height": self.det_height,
            "left_edges": self.left_edges,
            "topic": self.hist_topic,
            "source": self.source,
            "id": self._unique_id,
        }
        if self.input_schema:
            config["input_schema"] = self.input_schema
        return config

    def doInfo(self):
        result = [
            (
                f"{self.name} histogram type",
                self.hist_type,
                self.hist_type,
                "",
                "general",
            )
        ]
        result.extend(hist_type_by_name[self.hist_type].get_info(**self._params))
        return result

    def doShutdown(self):
        self._update_status(status.OK, "")


class JustBinItDetector(Detector, KafkaStatusHandler):
    """A detector whose image channels are histograms made by just-bin-it.

    All attached images must be JustBinItImage channels; timers, monitors and
    counters work as in any Detector.

    A count with a time preset sends a start/stop window, so just-bin-it ends
    the job by itself. Counts that end before it are ended with a stop command.
    """

    parameters = {
        "command_topic": Param(
            "The topic to send just-bin-it commands to",
            type=str,
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "response_topic": Param(
            "The topic where just-bin-it responses appear",
            type=str,
            userparam=False,
            settable=False,
            mandatory=True,
        ),
        "ack_timeout": Param(
            "How long to wait for timeout on acknowledgement",
            type=int,
            default=5,
            unit="s",
            userparam=False,
            settable=False,
        ),
        "hist_schema": Param(
            "Which schema to use for histograms",
            type=oneof(*deserialiser_by_schema.keys()),
            default="hs01",
            userparam=False,
            settable=True,
        ),
        "event_schema": Param(
            "Which schema the event data uses",
            type=oneof(*input_schemas),
            default="ev44",
            userparam=False,
            settable=True,
        ),
        "finish_timeout": Param(
            "How long finish() waits for the final histograms of a count",
            type=floatrange(0),
            default=10,
            unit="s",
            userparam=False,
            settable=True,
        ),
    }

    parameter_overrides = {
        "unit": Override(default="events", settable=False, mandatory=False),
        "fmtstr": Override(default="%d"),
        "liveinterval": Override(type=floatrange(0.5), default=1),
        "pollinterval": Override(default=None, userparam=False, settable=False),
        "statustopic": Override(default="", mandatory=False),
    }
    _last_live = 0
    _ack_thread = None
    _exit_thread = False
    _stop_sent = False
    _stop_lock = None
    _command_sender = None
    _response_consumer = None
    _hist_subscriber = None
    _acknowledged = False
    hardware_access = True

    def doPreinit(self, mode):
        self._stop_lock = threading.Lock()
        Detector.doPreinit(self, mode)

        if mode == SIMULATION:
            return

        if self.statustopic:
            # Enable heartbeat monitoring
            KafkaStatusHandler.doPreinit(self, mode)
        self._command_sender = KafkaProducer.create(self.brokers)
        # Set up the response message consumer
        self._response_consumer = KafkaConsumer.create(self.brokers)
        self._response_consumer.subscribe([self.response_topic])
        if session.sessiontype != POLLER:
            topics = sorted({image.hist_topic for image in self._attached_images})
            self._hist_subscriber = KafkaSubscriber(self.brokers)
            self._hist_subscriber.subscribe(topics, self._on_histogram_messages)

    def _on_histogram_messages(self, messages):
        for _, message in messages:
            try:
                decoded = decode_histogram(message)
            except Exception as err:
                self.log.warning("could not decode histogram message: %s", err)
                continue
            if decoded:
                for image in self._attached_images:
                    image.on_histogram(*decoded)

    def doPrepare(self):
        self._exit_thread = False
        self._acknowledged = False
        self._ack_thread = None
        self._stop_sent = False
        self._stop_lock = threading.Lock()
        if self._cache:
            self._cache.put(self, "status", (status.OK, ""), time.time())
        Detector.doPrepare(self)

    def doStart(self):
        unique_id = f"nicos-{self.name}-{time.time_ns()}"
        self.log.debug("set unique id = %s", unique_id)

        config = self._create_config(unique_id)

        self.log.debug("Requesting just-bin-it to start counting")

        self._send_command(self.command_topic, json.dumps(config).encode())
        Detector.doStart(self)

        # Check for acknowledgement of the command being received
        self._ack_thread = createThread(
            "jbi-ack", self._check_for_ack, (unique_id, self.ack_timeout)
        )

    def _timer_preset(self):
        for timer in self._attached_timers:
            for name, value in self._channel_presets.get(timer, ()):
                if float(value) > 0:
                    return timer, name, float(value)
        return None, None, None

    def _check_for_ack(self, identifier, timeout_duration):
        timeout = int(time.time()) + timeout_duration
        acknowledged = False
        while not (acknowledged or self._exit_thread):
            message = self._response_consumer.poll(timeout_ms=50)
            if message:
                # check for kafka errors, ignore any expected otherwise log them:
                if message.error() is not None:
                    # _PARTITION_EOF: Broker: No more messages
                    if message.error().name() != "_PARTITION_EOF":
                        err = message.error()
                        self.log.warning(
                            f"Encountered Kafka error: {err.str()}, ({err.code()}/{err.name()})"
                        )
                    continue
                try:
                    msg = json.loads(message.value())
                except json.decoder.JSONDecodeError as e:
                    self.log.warning(
                        f"Could not decode '{message.value()}' as JSON: {repr(e)}"
                    )
                else:
                    if "msg_id" in msg and msg["msg_id"] == identifier:
                        acknowledged = self._handle_message(msg)
                        self._acknowledged = acknowledged
                        break
            # Check for timeout
            if not acknowledged and int(time.time()) > timeout:
                err_msg = (
                    "Count aborted as no acknowledgement received from "
                    "just-bin-it within timeout duration "
                    f"({timeout_duration} seconds)"
                )
                self.log.error(err_msg)
                self._cache.put(self, "status", (status.ERROR, err_msg), time.time())
                self._send_stop_once()
                break

    def _handle_message(self, msg):
        if "response" in msg and msg["response"] == "ACK":
            self.log.debug("Counting request acknowledged by just-bin-it")
            return True
        elif "response" in msg and msg["response"] == "ERR":
            err_msg = msg.get("message", "just-bin-it rejected the request")
            self.log.error("just-bin-it could not start counting: %s", err_msg)
            self._cache.put(self, "status", (status.ERROR, err_msg), time.time())
        else:
            err_msg = "Unknown response message received from just-bin-it"
            self.log.error(err_msg)
            self._cache.put(self, "status", (status.ERROR, err_msg), time.time())
        return False

    def _send_command(self, topic, message):
        if self._command_sender is not None:
            self._command_sender.produce(topic, message)

    def _create_config(self, identifier):
        histograms = [
            image.get_configuration(f"{identifier}-{image.name}")
            for image in self._attached_images
        ]
        start_ms = int(time.time() * 1000)
        config_base = {
            "cmd": "config",
            "msg_id": identifier,
            "input_schema": self.event_schema,
            "output_schema": self.hist_schema,
            "histograms": histograms,
            "start": start_ms,
        }
        _, _, seconds = self._timer_preset()
        if seconds:
            config_base["stop"] = start_ms + round(seconds * 1000)
        return config_base

    def _send_stop_once(self):
        with self._stop_lock:
            if self._stop_sent:
                return
            self._stop_sent = True
        self._send_command(self.command_topic, b'{"cmd": "stop"}')

    def doShutdown(self):
        self._do_stop()
        if self._hist_subscriber is not None:
            self._hist_subscriber.close()
        if self._response_consumer is not None:
            self._response_consumer.close()
        KafkaStatusHandler.doShutdown(self)

    def doStop(self):
        self._do_stop()
        Detector.doStop(self)

    def doFinish(self):
        self._stop_job_threads()
        timer, name, seconds = self._timer_preset()
        if seconds and timer.presetReached(name, seconds, 0):
            self._wait_for_final_histograms()
        else:
            # just-bin-it keeps counting for seconds after a stop, so its
            # FINISHED histograms overshoot: keep the last update instead
            self._send_stop_once()
            if not self._acknowledged:
                self.log.warning(
                    "just-bin-it did not acknowledge the count before it ended: "
                    "the values do not cover the count"
                )
        Detector.doFinish(self)

    def _wait_for_final_histograms(self):
        channels = self._attached_images
        deadline = time.monotonic() + self.finish_timeout
        for channel in channels:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not channel.wait_finished(remaining):
                break
        missing = [channel.name for channel in channels if not channel.finished]
        if missing:
            self.log.warning(
                "no final histogram from just-bin-it within %s s for %s: "
                "the values are the last intermediate ones",
                self.finish_timeout,
                ", ".join(missing),
            )

    def _do_stop(self):
        self._stop_job_threads()
        self._send_stop_once()

    def _stop_job_threads(self):
        self._exit_thread = True
        self.stop_consuming(self._ack_thread)

    def stop_consuming(self, thread):
        if thread and thread.is_alive():
            thread.join()

    def doStatus(self, maxage=0):
        curstatus = self._cache.get(self, "status")
        if curstatus and curstatus[0] == status.ERROR:
            return curstatus
        return Detector.doStatus(self, maxage)

    def _status_update_callback(self, messages):
        # Called on heartbeat received
        if (
            self._mode == MASTER
            and self._cache.get(self, "status") == DISCONNECTED_STATE
        ):
            self._cache.put(self, "status", (status.OK, ""), time.time())

    def no_messages_callback(self):
        if self._mode == MASTER and not self.is_process_running():
            # No heartbeat
            self._cache.put(self, "status", DISCONNECTED_STATE, time.time())

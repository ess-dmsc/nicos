from time import sleep

import numpy as np
from streaming_data_types import deserialise_f144, deserialise_da00
from streaming_data_types.dataarray_da00 import Variable, serialise_da00
from streaming_data_types.utils import get_schema

from nicos import session
from nicos.core import (
    Readable,
    Param,
    listof,
    host,
    tupleof,
    POLLER,
    SIMULATION,
    MASTER,
    status,
    LIVE,
    ArrayDesc,
    Override,
)
from nicos.utils import byteBuffer
from nicos_ess.devices.kafka.consumer import KafkaSubscriber


def gen_image():
    y = np.linspace(0, 1024 - 1, 1024)
    x = np.linspace(0, 1024 - 1, 1024)
    x, y = np.meshgrid(x, y)

    center_x = 1024 / 2
    center_y = 1024 / 2 + 1024 * 0.1

    sigma_x = 1024 / 8
    sigma_y = 1024 / 4

    image = np.exp(
        -(
            ((x - center_x) ** 2) / (2 * sigma_x**2)
            + ((y - center_y) ** 2) / (2 * sigma_y**2)
        )
    )

    image += np.abs(np.random.normal(0, 0.1, image.shape))
    image *= 100.0
    image *= np.random.uniform(0.8, 1.2)

    return image


def gen_hist():
    """
    Generates count data to look like neutron instrument time-of-flight data.
    """
    NUM_BINS = 500
    NUM_EVENTS = 10000

    data_1 = np.random.normal(5000, 1000, NUM_EVENTS)
    data_2 = np.random.normal(10000, 2000, NUM_EVENTS)
    data = np.concatenate([data_1, data_2])
    hist, bin_edges = np.histogram(data, bins=NUM_BINS)
    return hist, bin_edges


class KafkaReadable(Readable):
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
        "source_name": Param(
            "Name of the source to filter messages",
            type=str,
            settable=True,
            mandatory=True,
        ),
        "curstatus": Param(
            "Store the current device status",
            internal=True,
            type=tupleof(int, str),
            settable=True,
        ),
        "curvalue": Param(
            "Store the current value",
            internal=True,
            settable=True,
            unit="main",
        ),
    }

    _kafka_subscriber = None

    def doPreinit(self, mode):
        if session.sessiontype != POLLER and mode != SIMULATION:
            self._kafka_subscriber = KafkaSubscriber(self.brokers)
            self._kafka_subscriber.subscribe(
                self.topic,
                self.new_messages_callback,
                self.no_messages_callback,
            )

        if self._mode == MASTER:
            self._setROParam("curstatus", (status.WARN, "Trying to connect..."))

    def doRead(self, maxage=0):
        return self.curvalue

    def doStatus(self, maxage=0):
        return self.curstatus

    def new_messages_callback(self, messages):
        raise NotImplementedError

    def no_messages_callback(self):
        pass

    def doShutdown(self):
        self._kafka_subscriber.close()


class F144Readable(KafkaReadable):
    def new_messages_callback(self, messages):
        for timestamp, message in messages:
            try:
                if get_schema(message) != "f144":
                    continue
                msg = deserialise_f144(message)

                if msg.source_name != self.source_name:
                    continue

                self._setROParam("curvalue", msg.value)
                self._setROParam("curstatus", (status.OK, ""))

            except Exception as e:
                self.log.warning("Could not decode message from topic: %s", e)
                self._setROParam(
                    "curstatus", (status.ERROR, "Could not decode message")
                )


class Da00Readable(KafkaReadable):
    data_structure = {}
    # source_name = "some_source"
    parameter_overrides = {"unit": Override(mandatory=False, default="")}

    def doInit(self, mode):
        pass
        # self._run_thread = threading.Thread(target=self._run, daemon=True)
        # self._run_thread.start()

    def _run(self):
        while True:
            self.fake_1d()
            self.fake_2d()
            sleep(0.5)

    def new_messages_callback(self, messages):
        for timestamp, message in messages:
            try:
                if get_schema(message) != "da00":
                    continue
                msg = deserialise_da00(message)
                # if msg.source_name != self.source_name:
                #     continue
                self.data_structure.clear()
                variables = msg.data
                self._parse_new_data(variables)
                self.update_arraydesc()

                if self.data_structure:
                    self.putResult(
                        1,
                        self.get_plot_data(),
                        timestamp,
                        msg.source_name,
                        self.data_structure["plot_type"],
                    )
            except Exception as e:
                print(f"Could not decode message from topic: {e}")

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

    def arrayInfo(self):
        return self.update_arraydesc()

    def update_arraydesc(self):
        if self.data_structure:
            return ArrayDesc(
                self.name, shape=self.data_structure["signal_shape"], dtype=np.int32
            )
        else:
            return ArrayDesc(self.name, shape=(), dtype=np.int32)

    def fake_1d(self, source_name="1d_source"):
        data, edges = gen_hist()

        NUM_EVENTS = len(data)

        var_1_1d = Variable(
            name="signal",
            data=data.astype(np.int32),
            shape=(NUM_EVENTS),
            axes=["bin_edges"],
            source=source_name,
        )

        var_2_1d = Variable(
            name="frame_time",
            data=edges.astype(np.int32),
            # data=np.array([0, 1, 2, 5, 6, 8, 11, 12, 13, 14, 20]).astype(np.int32),
            shape=len(edges),
            axes=["bin_edges"],
            source=source_name,
        )

        serialised_input_1d = {
            "source_name": source_name,
            "timestamp_ns": 123456,
            "data": [var_1_1d, var_2_1d],
        }

        message_1d = serialise_da00(**serialised_input_1d)

        self.new_messages_callback([(123456, message_1d)])

    def fake_2d(self, source_name="2d_source"):
        size = 1024

        shape = (size, size)
        # NUM_EVENTS = shape[0] * shape[1]

        var_1_2d = Variable(
            name="signal",
            data=gen_image().astype(np.int32),
            shape=shape,
            axes=["x", "y"],
            source=source_name,
        )

        var_2_2d = Variable(
            name="frame_time",
            data=np.array([i for i in range(shape[0])]).astype(np.int32),
            shape=(shape[0]),
            axes=["x"],
            source=source_name,
        )

        var_3_2d = Variable(
            name="frame_time",
            data=np.array([i * 2 + 100 for i in range(shape[1])]).astype(np.int64),
            shape=(shape[0]),
            axes=["y"],
            source=source_name,
        )

        serialised_input_2d = {
            "source_name": source_name,
            "timestamp_ns": 123456,
            "data": [var_1_2d, var_2_2d, var_3_2d],
        }

        message_2d = serialise_da00(**serialised_input_2d)

        self.new_messages_callback([(123456, message_2d)])


if __name__ == "__main__":
    from streaming_data_types.dataarray_da00 import Variable, serialise_da00

    da00_readable = Da00Readable()

    # Example message
    NUM_EVENTS = 10

    var_1_1d = Variable(
        name="signal",
        data=np.array([i % 256 for i in range(NUM_EVENTS)]).astype(np.int32),
        shape=(NUM_EVENTS),
        axes=["bin_edges"],
        source="some_source",
    )

    var_2_1d = Variable(
        name="frame_time",
        data=np.array([i % 256 for i in range(NUM_EVENTS + 1)]).astype(np.int32),
        shape=(NUM_EVENTS + 1),
        axes=["bin_edges"],
        source="some_source",
    )

    serialised_input_1d = {
        "source_name": "some_source",
        "timestamp_ns": 123456,
        "data": [var_1_1d, var_2_1d],
    }

    message_1d = serialise_da00(**serialised_input_1d)

    da00_readable.new_messages_callback([(123456, message_1d)])

    to_plot_list = da00_readable.get_plot_data()

    for data in to_plot_list:
        print(data)

    # Example message
    NUM_EVENTS = 16

    var_1_2d = Variable(
        name="signal",
        data=np.array([i % 256 for i in range(NUM_EVENTS)])
        .astype(np.int32)
        .reshape(4, 4),
        shape=(NUM_EVENTS),
        axes=["x", "y"],
        source="some_source",
    )

    var_2_2d = Variable(
        name="frame_time",
        data=np.array([i * 2 % 256 for i in range(NUM_EVENTS // 4)]).astype(np.int32),
        shape=(NUM_EVENTS // 4),
        axes=["x"],
        source="some_source",
    )

    var_3_2d = Variable(
        name="frame_time",
        data=np.array([i % 256 for i in range(NUM_EVENTS // 4)]).astype(np.int32),
        shape=(NUM_EVENTS // 4),
        axes=["y"],
        source="some_source",
    )

    serialised_input_2d = {
        "source_name": "some_source",
        "timestamp_ns": 123456,
        "data": [var_1_2d, var_2_2d, var_3_2d],
    }

    message_2d = serialise_da00(**serialised_input_2d)

    da00_readable.new_messages_callback([(123456, message_2d)])

    to_plot_list = da00_readable.get_plot_data()

    for data in to_plot_list:
        print(data)

import time

# Common librdkafka offset constants
OFFSET_BEGINNING = -2
OFFSET_END = -1
OFFSET_INVALID = -1001  # rd_kafka.h: RD_KAFKA_OFFSET_INVALID


class _ClusterState:
    def __init__(self):
        self.messages = {}
        self.metadata = Metadata()


class Message:
    def __init__(self, topic, partition, offset, key, value, error=None):
        self._topic = topic
        self._partition = partition
        self._offset = offset
        self._key = key
        self._value = value
        self._error = error
        self._timestamp = time.time()

    def value(self):
        return self._value

    def offset(self):
        return self._offset

    def error(self):
        return self._error

    def topic(self):
        return self._topic

    def partition(self):
        return self._partition

    def key(self):
        return self._key

    def timestamp(self):
        return self._timestamp


class ExceptionMessage(Message):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def value(self):
        raise Exception("Value method called on ExceptionMessage")

    def offset(self):
        raise Exception("Offset method called on ExceptionMessage")

    def error(self):
        raise Exception("Error method called on ExceptionMessage")


class TopicPartition:
    def __init__(self, topic, partition, offset=0):
        self.topic = topic
        self.partition = partition
        self.offset = offset


class PartitionMetadata:
    def __init__(self, partition_id):
        self.partition_id = partition_id


class TopicMetadata:
    def __init__(self, topic_name, num_partitions=1):
        self.topic_name = topic_name
        self.error = None
        self.partitions = {
            partition_id: PartitionMetadata(partition_id)
            for partition_id in range(num_partitions)
        }


class Metadata:
    def __init__(self):
        self.topics = {}

    def add_topic(self, topic_name, num_partitions=1):
        self.topics[topic_name] = TopicMetadata(topic_name, num_partitions)


class ConsumerStub:
    _clusters = {}

    def __init__(self, config={"auto.offset.reset": "earliest"}):
        self.config = config
        self.messages = {}
        self.current_offsets = {}
        self._pos_known = {}
        self.assigned_partitions = []
        self._metadata = Metadata()
        self.poll_index = 0
        self._closed = False
        self._paused = set()

        bs = config.get("bootstrap.servers", "default-cluster")
        gid = config.get("group.id") or config.get("group_id") or "default-group"
        cluster_id = f"{bs}|{gid}"

        cluster = ConsumerStub._clusters.setdefault(cluster_id, _ClusterState())

        # Shared across instances of the same cluster_id:
        self.messages = cluster.messages
        self._metadata = cluster.metadata

    @classmethod
    def clear_all_clusters(cls):
        """Nuke all clusters (useful if you want a global reset)."""
        cls._clusters.clear()

    def add_message(self, topic, partition, offset, key, value, error=None):
        self.messages.setdefault(topic, {}).setdefault(partition, []).append(
            Message(topic, partition, offset, key, value, error)
        )

    def add_exception_message(self, topic, partition, offset, key, value, error=None):
        self.messages.setdefault(topic, {}).setdefault(partition, []).append(
            ExceptionMessage(topic, partition, offset, key, value, error)
        )

    def create_topic(self, topic_name, num_partitions=1):
        if topic_name not in self._metadata.topics:
            self._metadata.add_topic(topic_name, num_partitions)
        self.current_offsets.setdefault(topic_name, {})
        self._pos_known.setdefault(topic_name, {})
        for p in range(num_partitions):
            self.current_offsets[topic_name].setdefault(p, 0)
            self._pos_known[topic_name].setdefault(p, False)

    def poll(self, timeout=None):
        if self._closed:
            raise RuntimeError("Consumer is closed")
        if timeout == 0:
            return None
        if not self.assigned_partitions:
            return None

        start_index = self.poll_index
        while True:
            tp = self.assigned_partitions[self.poll_index]
            topic, partition = tp.topic, tp.partition

            if (topic, partition) not in self._paused:
                cur = self.current_offsets.get(topic, {}).get(partition, OFFSET_INVALID)
                msgs = self.messages.get(topic, {}).get(partition, [])
                if isinstance(cur, int) and cur >= 0 and cur < len(msgs):
                    msg = msgs[cur]
                    # advance next-to-consume and mark position known
                    self.current_offsets[topic][partition] = cur + 1
                    self._pos_known.setdefault(topic, {})[partition] = True
                    self.poll_index = (self.poll_index + 1) % len(
                        self.assigned_partitions
                    )
                    return msg

            self.poll_index = (self.poll_index + 1) % len(self.assigned_partitions)
            if self.poll_index == start_index:
                return None

    def consume(self, num_messages=1, timeout=-1):
        if self._closed:
            raise RuntimeError("Consumer is closed")
        msgs = []
        for _ in range(max(0, int(num_messages))):
            m = self.poll(timeout if timeout is not None else None)
            if m is None:
                break
            msgs.append(m)
        return msgs

    def close(self):
        self._closed = True
        self.assigned_partitions = []
        self._paused.clear()

    def unsubscribe(self):
        self.assigned_partitions = []
        self._paused.clear()

    def unassign(self):
        self.assigned_partitions = []
        self._paused.clear()
        self.poll_index = 0

    def assignment(self):
        return list(self.assigned_partitions)

    def commit(self, asynchronous=False):
        return None

    def subscribe(self, topics):
        self.assigned_partitions = []
        for topic in topics:
            if topic not in self._metadata.topics:
                self._metadata.add_topic(topic, 1)

            self.current_offsets.setdefault(topic, {})
            self._pos_known.setdefault(topic, {})
            num_parts = len(self._metadata.topics[topic].partitions)
            for p in range(num_parts):
                # set initial next-to-consume; but mark as unknown position until fetch/seek
                if p not in self.current_offsets[topic]:
                    if self.config.get("auto.offset.reset", "earliest") == "latest":
                        self.current_offsets[topic][p] = len(
                            self.messages.get(topic, {}).get(p, [])
                        )
                    else:
                        self.current_offsets[topic][p] = 0
                self._pos_known[topic][p] = False
                self.assigned_partitions.append(TopicPartition(topic, p))

    def list_topics(self, topic=None, timeout=None):
        # Do not mutate metadata here; just return the current view
        return self._metadata

    def assign(self, topic_partitions):
        self.assigned_partitions = []
        for tp in topic_partitions:
            topic, partition, offset = tp.topic, tp.partition, tp.offset

            if topic not in self._metadata.topics:
                num_parts = max(1, len(self.messages.get(topic, {})) or 1)
                self._metadata.add_topic(topic, num_parts)

            self.current_offsets.setdefault(topic, {})
            self._pos_known.setdefault(topic, {})

            # set numeric offset but mark as unknown until fetch/seek
            if isinstance(offset, int) and offset >= 0:
                self.current_offsets[topic][partition] = offset
            else:
                self.current_offsets[topic].setdefault(partition, OFFSET_INVALID)

            self._pos_known[topic][partition] = False
            self.assigned_partitions.append(TopicPartition(topic, partition, offset))

        self.poll_index = 0

    def get_watermark_offsets(self, tp, timeout=None, cached=False):
        topic, partition = tp.topic, tp.partition
        if topic in self.messages and partition in self.messages[topic]:
            high = len(self.messages[topic][partition])
            low = 0
            return low, high
        return 0, 0

    def position(self, partitions):
        out = []
        for tp in partitions:
            topic, partition = tp.topic, tp.partition
            if self._pos_known.get(topic, {}).get(partition, False):
                off = self.current_offsets.get(topic, {}).get(partition, OFFSET_INVALID)
            else:
                off = OFFSET_INVALID
            out.append(TopicPartition(topic, partition, off))
        return out

    def seek(self, tp):
        topic, partition, off = tp.topic, tp.partition, tp.offset
        self.current_offsets.setdefault(topic, {})
        self._pos_known.setdefault(topic, {})
        msgs = self.messages.get(topic, {}).get(partition, [])

        if off == OFFSET_BEGINNING:
            self.current_offsets[topic][partition] = 0
            self._pos_known[topic][partition] = True
        elif off == OFFSET_END:
            self.current_offsets[topic][partition] = len(msgs)
            self._pos_known[topic][partition] = True
        elif isinstance(off, int) and off >= 0:
            self.current_offsets[topic][partition] = off
            self._pos_known[topic][partition] = True
        else:
            # keep unknown
            self._pos_known[topic][partition] = False

    def pause(self, partitions):
        for tp in partitions:
            self._paused.add((tp.topic, tp.partition))

    def resume(self, partitions):
        for tp in partitions:
            self._paused.discard((tp.topic, tp.partition))

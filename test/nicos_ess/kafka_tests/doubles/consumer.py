import time


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
    def __init__(self, config={"auto.offset.reset": "earliest"}):
        self.config = config
        self.messages = {}
        self.current_offsets = {}
        self.assigned_partitions = []
        self._metadata = Metadata()
        self.poll_index = 0

    def add_message(self, topic, partition, offset, key, value, error=None):
        if topic not in self.messages:
            self.messages[topic] = {}
        if partition not in self.messages[topic]:
            self.messages[topic][partition] = []
        message = Message(topic, partition, offset, key, value, error)
        self.messages[topic][partition].append(message)

    def add_exception_message(self, topic, partition, offset, key, value, error=None):
        if topic not in self.messages:
            self.messages[topic] = {}
        if partition not in self.messages[topic]:
            self.messages[topic][partition] = []
        message = ExceptionMessage(topic, partition, offset, key, value, error)
        self.messages[topic][partition].append(message)

    def poll(self, timeout=None):
        if not self.assigned_partitions:
            return None

        start_index = self.poll_index
        while True:
            tp = self.assigned_partitions[self.poll_index]
            topic = tp.topic
            partition = tp.partition
            current_offset = self.current_offsets[topic][partition]
            messages = self.messages.get(topic, {}).get(partition, [])

            if current_offset < len(messages):
                msg = messages[current_offset]
                self.current_offsets[topic][partition] += 1
                self.poll_index = (self.poll_index + 1) % len(self.assigned_partitions)
                return msg

            self.poll_index = (self.poll_index + 1) % len(self.assigned_partitions)

            if self.poll_index == start_index:
                return None

    def consume(self, num_messages, timeout=None):
        msgs = []
        for _ in range(num_messages):
            msg = self.poll(timeout)
            if msg is None:
                break
            msgs.append(msg)
        return msgs

    def close(self):
        self.unsubscribe()
        self.unassign()
        self.messages = {}
        self.current_offsets = {}
        self._metadata = Metadata()

    def unsubscribe(self):
        self.assigned_partitions = []
        self.current_offsets = {}
        # self._metadata = Metadata()

    def unassign(self):
        self.assigned_partitions = []
        self.current_offsets = {}
        self._metadata = Metadata()

    def assignment(self):
        return self.assigned_partitions

    def commit(self, asynchronous=False):
        pass

    def subscribe(self, topics):
        self.assigned_partitions = []
        for topic in topics:
            if topic not in self._metadata.topics:
                num_partitions = len(self.messages.get(topic, {}))
                if num_partitions == 0:
                    num_partitions = 1  # Default to 1 partition if none exist
                self._metadata.add_topic(topic, num_partitions)

            if topic not in self.current_offsets:
                self.current_offsets[topic] = {}

            num_partitions = len(self._metadata.topics[topic].partitions)
            for partition in range(num_partitions):
                if partition not in self.current_offsets[topic]:
                    if self.config.get("auto.offset.reset", "earliest") == "latest":
                        self.current_offsets[topic][partition] = len(
                            self.messages.get(topic, {}).get(partition, [])
                        )
                    else:
                        self.current_offsets[topic][partition] = 0

                tp = TopicPartition(topic, partition)
                self.assigned_partitions.append(tp)

    def create_topic(self, topic_name, num_partitions=1):
        if topic_name not in self._metadata.topics:
            self._metadata.add_topic(topic_name, num_partitions)

    def list_topics(self, topic=None, timeout=None):
        if topic is not None and topic not in self._metadata.topics:
            num_partitions = len(self.messages.get(topic, {}))
            if num_partitions == 0:
                num_partitions = 1
            self._metadata.add_topic(topic, num_partitions)

        return self._metadata

    def assign(self, topic_partitions):
        self.assigned_partitions = topic_partitions
        for tp in topic_partitions:
            topic = tp.topic
            partition = tp.partition
            offset = tp.offset
            if topic not in self._metadata.topics:
                num_partitions = len(self.messages.get(topic, {}))
                if num_partitions == 0:
                    num_partitions = 1
                self._metadata.add_topic(topic, num_partitions)

            if topic not in self.current_offsets:
                self.current_offsets[topic] = {}
            self.current_offsets[topic][partition] = offset

    def get_watermark_offsets(self, tp):
        topic, partition = tp.topic, tp.partition
        if topic in self.messages and partition in self.messages[topic]:
            high_watermark = len(self.messages[topic][partition])
            return 0, high_watermark
        return 0, 0

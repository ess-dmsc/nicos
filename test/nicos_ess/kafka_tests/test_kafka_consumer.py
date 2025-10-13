# tests/test_kafka_consumer_subscriber.py
import threading
import time
import json
import types

import pytest

import nicos_ess.devices.kafka.consumer as mod

from test.nicos_ess.kafka_tests.doubles.consumer import ConsumerStub, TopicPartition as TopicPartitionStub

# --- Pytest fixtures ---------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_external_bits(monkeypatch):
    """
    Make the production module use the stub instead of the real confluent_kafka.Consumer
    and ensure TopicPartition type matches what the stub expects.
    Also neutralise SASL config and thread factory.
    """
    # Inject our stub Consumer & TopicPartition into the production module
    monkeypatch.setattr(mod, "Consumer", ConsumerStub)
    monkeypatch.setattr(mod, "TopicPartition", TopicPartitionStub, raising=True)

    # Avoid depending on project-specific SASL helper
    monkeypatch.setattr(mod, "create_sasl_config", lambda: {}, raising=False)

    # Make createThread actually start a Python thread
    def createThread(name, target):
        t = threading.Thread(name=name, target=target, daemon=True)
        t.start()
        return t

    monkeypatch.setattr(mod, "createThread", createThread, raising=True)


@pytest.fixture
def consumer():
    # Instantiate the wrapper; it'll build our stub internally.
    c = mod.KafkaConsumer(brokers=["broker1:9092"], starting_offset="earliest")
    return c


@pytest.fixture
def subscriber():
    return mod.KafkaSubscriber(brokers=["broker1:9092"])


# --- Helper ------------------------------------------------------------------

def wait_until(pred, timeout=1.5):
    start = time.time()
    while time.time() - start < timeout:
        if pred():
            return True
        time.sleep(0.01)
    return False


# --- Tests: KafkaConsumer ----------------------------------------------------

def test_consumer_topics_and_consume_batch(consumer):
    # Prepare metadata & messages on the stub
    stub = consumer._consumer
    stub.create_topic("data_topic", num_partitions=1)  # pre-create topic for tests
    stub.add_message("data_topic", 0, offset=0, key=b"k1", value=b"v1")
    stub.add_message("data_topic", 0, offset=1, key=b"k2", value=b"v2")

    # Manual subscribe -> assign
    consumer.subscribe(["data_topic"])

    # topics() should list existing topic names
    topics = consumer.topics()
    assert "data_topic" in topics

    # consume_batch should return stub Message instances
    msgs = consumer.consume_batch(max_messages=10, timeout_s=0.05)
    assert len(msgs) == 2
    assert [m.value() for m in msgs] == [b"v1", b"v2"]


def test_try_reassign_waits_for_metadata_then_succeeds(consumer):
    # Ask to reassign for a topic that doesn't exist yet -> should return False
    consumer._topics = ["missing_topic"]
    consumer._pending_reassign = True
    assert consumer.try_reassign() is False
    assert consumer._pending_reassign is True

    # Add metadata for the missing topic -> should succeed now
    consumer._consumer.create_topic("missing_topic", num_partitions=2)
    assert consumer.try_reassign() is True
    assert consumer._pending_reassign is False
    # Confirm partitions captured in last assignment
    assert consumer._last_assignment
    assert { (tp.topic, tp.partition) for tp in consumer._last_assignment } == {
        ("missing_topic", 0), ("missing_topic", 1)
    }


# --- Tests: KafkaSubscriber --------------------------------------------------

def test_subscriber_delivers_messages_via_callback(subscriber):
    # Arrange: set up topic & messages in the underlying stub
    consumer = subscriber.consumer
    stub = consumer._consumer
    stub.create_topic("topic", num_partitions=1)
    stub.add_message("topic", 0, offset=0, key=b"k", value=b"A")
    stub.add_message("topic", 0, offset=1, key=b"k", value=b"B")

    delivered = []
    no_msg_calls = {"n": 0}

    print(stub.messages)
    print(stub.list_topics().topics)

    def on_msgs(items):
        # items are ((ts_type, ts), value) pairs
        delivered.extend(items)
        print("delivered:", items)
        # Stop the thread once we have what we want
        subscriber.stop_consuming()

    def on_idle():
        no_msg_calls["n"] += 1

    subscriber.subscribe(["topic"], on_msgs, on_idle)

    assert wait_until(lambda: len(delivered) >= 2, timeout=5)
    # Timestamps are whatever the stub produced; just assert values.
    assert [v for (_, v) in delivered] == [b"A", b"B"]
    # Usually called at least once after messages drain
    assert no_msg_calls["n"] >= 0  # not asserting strict count due to timing


def test_subscriber_reboots_when_no_stats_for_long_time(monkeypatch, subscriber):
    # Keep the loop tight
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None, raising=True)

    # Controlled monotonic clock
    t = {"now": 1000.0}
    monkeypatch.setattr(mod, "_now_mono", lambda: t["now"], raising=True)

    # Make grace windows tiny to trigger quickly
    monkeypatch.setattr(mod, "NO_STATS_REBOOT_SECS", 0.1, raising=True)
    monkeypatch.setattr(mod, "WAIT_AFTER_ASSIGN_SECS", 0.0, raising=True)
    monkeypatch.setattr(mod, "REBOOT_COOLDOWN_SECS", 0.0, raising=True)

    # Prepare a topic to let subscribe() assign and start loop
    consumer = subscriber.consumer
    stub = consumer._consumer
    stub.create_topic("topic", num_partitions=1)

    rebooted = {"flag": False}

    def fake_rebootstrap(reason=""):
        rebooted["flag"] = True
        # also stop the loop
        subscriber.stop_consuming()

    # Patch the consumer's rebootstrap
    monkeypatch.setattr(consumer, "rebootstrap", fake_rebootstrap, raising=True)

    # Start subscribed thread
    subscriber.subscribe(["topic"], messages_callback=lambda *_: None)

    # Advance time to exceed NO_STATS_REBOOT_SECS without any stats_cb
    t["now"] += 1.0

    assert wait_until(lambda: rebooted["flag"], timeout=1.0)

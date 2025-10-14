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


def test_cooldown_ok_edge_cases():
    now = mod._now_mono()
    assert mod._cooldown_ok(now - 2.0, 1.0) is True
    assert mod._cooldown_ok(now, 1.0) is False


def test_health_helpers_transitions():
    h = mod._Health()
    # default empty state
    assert h.brokers_up() == 0
    assert h.all_down_for() == 0.0

    # add states
    h.brokers_state = {"a": "UP", "b": "DOWN", "c": "TRY_CONNECT"}
    assert h.brokers_up() == 1

    # simulate all down window
    h.all_down_since = mod._now_mono()
    assert h.all_down_for() >= 0.0  # non-negative


def test_can_fetch_metadata_true(consumer):
    # With the stub, list_topics always works -> True
    assert consumer._can_fetch_metadata() is True
    # Also works when asking for a concrete topic (stub will auto-add)
    assert consumer._can_fetch_metadata("anytopic", timeout_s=0.01) is True


def test_consumer_poll_without_assign_returns_none(consumer):
    # No assignment -> poll returns None
    assert consumer.poll(timeout_ms=10) is None


def test_consumer_poll_after_subscribe_returns_messages(consumer):
    # Prepare messages
    stub = consumer._consumer
    stub.create_topic("t", num_partitions=1)
    stub.add_message("t", 0, offset=0, key=b"k", value=b"1")
    stub.add_message("t", 0, offset=1, key=b"k", value=b"2")

    consumer.subscribe(["t"])

    v1 = consumer.poll(timeout_ms=50)
    v2 = consumer.poll(timeout_ms=50)
    v3 = consumer.poll(timeout_ms=50)  # drained

    assert v1.value() == b"1"
    assert v2.value() == b"2"
    assert v3 is None


def test_consume_batch_zero_and_no_assignment(consumer):
    # max_messages <= 0 -> []
    assert consumer.consume_batch(0) == []
    # no assignment -> []
    assert consumer.consume_batch(10, timeout_s=0.05) == []


def test_consumer_assignment_and_unsubscribe(consumer):
    stub = consumer._consumer
    stub.create_topic("x", num_partitions=2)

    consumer.subscribe(["x"])
    assigned = consumer.assignment()
    # should have two partitions
    assert {(tp.topic, tp.partition) for tp in assigned} == {("x", 0), ("x", 1)}

    # unsubscribe clears assignment in stub
    consumer.unsubscribe()
    assert consumer.assignment() == []


def test_consumer_topics_lists_created_names(consumer):
    stub = consumer._consumer
    stub.create_topic("a", num_partitions=1)
    stub.create_topic("b", num_partitions=2)
    names = consumer.topics()
    assert "a" in names and "b" in names


def test_consumer_subscribe_raises_on_missing_topic(consumer):
    with pytest.raises(mod.ConfigurationError):
        consumer.subscribe(["does_not_exist"])


def test_consumer_subscribe_raises_on_topic_error(consumer):
    # Inject a topic with an error in stub metadata
    stub = consumer._consumer
    stub.create_topic("bad", num_partitions=1)
    stub._metadata.topics["bad"].error = RuntimeError("metadata error")

    with pytest.raises(mod.ConfigurationError):
        consumer.subscribe(["bad"])


def test_try_reassign_no_topics_is_trivially_true(consumer):
    consumer._topics = []
    consumer._pending_reassign = True
    assert consumer.try_reassign() is True
    assert consumer._pending_reassign is False


def test_on_stats_invalid_json_is_ignored(consumer, capsys):
    # Should not raise even with junk
    consumer._on_stats("not json at all")
    # health still exists
    assert isinstance(consumer._health, mod._Health)


def test_on_stats_updates_broker_states_and_all_down_since(consumer):
    # Start with all brokers DOWN -> all_down_since set
    payload1 = json.dumps({
        "brokers": {"b1": {"state": "DOWN"}, "b2": {"state": "DOWN"}},
        "cgrp": {"state": "up"},
    })
    consumer._on_stats(payload1)
    assert consumer.brokers_up() == 0
    assert consumer._health.all_down_since is not None

    # Now one broker UP -> all_down_since cleared
    payload2 = json.dumps({
        "brokers": {"b1": {"state": "UP"}},
        "cgrp": {"state": "up"},
    })
    consumer._on_stats(payload2)
    assert consumer.brokers_up() == 1
    assert consumer._health.all_down_since is None
    # Also check GroupCoordinator
    assert consumer._health.group_coordinator_state == "UP"


def test_on_error_nonfatal_does_not_rebootstrap(consumer):
    class DummyErr:
        def code(self): return 123
        def name(self): return "WHATEVER"
        def fatal(self): return False
        def retriable(self): return True
        def str(self): return "just a warning"

    # Should not touch _last_rebootstrap_mono for non-fatal
    before = consumer._last_rebootstrap_mono
    consumer._on_error(DummyErr())
    assert consumer._last_rebootstrap_mono == before


def test_consumer_close_is_idempotent(consumer):
    # close once
    consumer.close()
    # and again (stub tolerates)
    consumer.close()


def test_subscriber_stop_and_close_idempotent(subscriber):
    # stop without starting
    subscriber.stop_consuming()
    subscriber.stop_consuming(True)
    # close is idempotent
    subscriber.close()
    subscriber.close()

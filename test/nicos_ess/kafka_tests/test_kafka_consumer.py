import json
import pytest

import nicos_ess.devices.kafka.consumer as mod
from test.nicos_ess.kafka_tests.doubles.consumer import (
    ConsumerStub,
    TopicPartition as TopicPartitionStub,
)


class FakeClock:
    def __init__(self, start=0.0):
        self.t = float(start)

    def now(self):
        return self.t

    def sleep(self, dt):
        self.t += float(dt)


def pump(sub, steps=200):
    """Run a bounded number of ticks to drive the subscriber without threads."""
    for _ in range(steps):
        sub.tick()


@pytest.fixture
def clock():
    return FakeClock(start=1000.0)


@pytest.fixture
def consumer(clock):
    """KafkaConsumer wired to the stub via clean DI (no global monkeypatch)."""
    c = mod.KafkaConsumer(
        brokers=["broker1:9092"],
        starting_offset="earliest",
        consumer_factory=lambda conf: ConsumerStub(conf),
        topic_partition_factory=lambda t, p, o=None: TopicPartitionStub(
            t, p, o if o is not None else 0
        ),
        now=clock.now,
        sleep=clock.sleep,
        rand_uniform=lambda a, b: 0.0,  # deterministic jitter in tests
    )
    return c


@pytest.fixture
def subscriber(clock, consumer):
    """Subscriber using the injected consumer and a synchronous tick loop."""
    sub = mod.KafkaSubscriber(
        consumer=consumer,
        no_stats_secs=1.0,             # speed up tests
        all_down_secs=1.0,             # speed up tests
        cooldown_secs=0.5,             # speed up tests
        wait_after_assign_secs=0.2,    # speed up tests
        stuck_with_lag_secs=0.8,       # fast stuck detection for tests
        min_lag_for_stuck=1,           # only reboot when lag >= 2
        now=clock.now,
        sleep=clock.sleep,
        use_thread=False,              # run synchronously in tests
    )
    return sub


def test_consumer_topics_and_consume_batch(consumer):
    stub = consumer._consumer
    stub.create_topic("data_topic", num_partitions=1)
    stub.add_message("data_topic", 0, offset=0, key=b"k1", value=b"v1")
    stub.add_message("data_topic", 0, offset=1, key=b"k2", value=b"v2")

    consumer.subscribe(["data_topic"])

    topics = consumer.topics()
    assert "data_topic" in topics

    msgs = consumer.consume_batch(max_messages=10, timeout_s=0.05)
    assert len(msgs) == 2
    assert [m.value() for m in msgs] == [b"v1", b"v2"]


def test_try_reassign_waits_for_metadata_then_succeeds(consumer):
    consumer._topics = ["missing_topic"]
    consumer._pending_reassign = True
    assert consumer.try_reassign() is False
    assert consumer._pending_reassign is True

    consumer._consumer.create_topic("missing_topic", num_partitions=2)
    assert consumer.try_reassign() is True
    assert consumer._pending_reassign is False
    assert consumer._last_assignment
    assert {(tp.topic, tp.partition) for tp in consumer._last_assignment} == {
        ("missing_topic", 0),
        ("missing_topic", 1),
    }


def test_consumer_poll_after_subscribe_returns_messages(consumer):
    stub = consumer._consumer
    stub.create_topic("t", num_partitions=1)
    stub.add_message("t", 0, offset=0, key=b"k", value=b"1")
    stub.add_message("t", 0, offset=1, key=b"k", value=b"2")

    consumer.subscribe(["t"])

    v1 = consumer.poll(timeout_ms=50)
    v2 = consumer.poll(timeout_ms=50)
    v3 = consumer.poll(timeout_ms=50)
    assert v1.value() == b"1"
    assert v2.value() == b"2"
    assert v3 is None


def test_consume_batch_zero_and_no_assignment(consumer):
    assert consumer.consume_batch(0) == []
    # no assignment -> []
    assert consumer.consume_batch(10, timeout_s=0.05) == []


def test_consumer_assignment_and_unsubscribe(consumer):
    stub = consumer._consumer
    stub.create_topic("x", num_partitions=2)

    consumer.subscribe(["x"])
    assigned = consumer.assignment()
    assert {(tp.topic, tp.partition) for tp in assigned} == {("x", 0), ("x", 1)}

    consumer.unsubscribe()
    assert consumer.assignment() == []


def test_consumer_subscribe_raises_on_missing_topic(consumer):
    with pytest.raises(mod.ConfigurationError):
        consumer.subscribe(["does_not_exist"])


def test_consumer_subscribe_raises_on_topic_error(consumer):
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


def test_on_stats_invalid_json_is_ignored(consumer):
    consumer._on_stats("not json at all")
    assert isinstance(consumer._health, mod._Health)


def test_on_stats_updates_broker_states_and_all_down_since(consumer):
    payload1 = json.dumps(
        {
            "brokers": {"b1": {"state": "DOWN"}, "b2": {"state": "DOWN"}},
            "cgrp": {"state": "up"},
        }
    )
    consumer._on_stats(payload1)
    assert consumer.brokers_up() == 0
    assert consumer._health.all_down_since is not None

    payload2 = json.dumps({"brokers": {"b1": {"state": "UP"}}, "cgrp": {"state": "up"}})
    consumer._on_stats(payload2)
    assert consumer.brokers_up() == 1
    assert consumer._health.all_down_since is None
    assert consumer._health.group_coordinator_state == "UP"


def test_on_error_nonfatal_does_not_rebootstrap(consumer):
    class DummyErr:
        def code(self):
            return 123

        def name(self):
            return "WHATEVER"

        def fatal(self):
            return False

        def retriable(self):
            return True

        def str(self):
            return "just a warning"

    before = consumer._last_rebootstrap_mono
    consumer._on_error(DummyErr())
    assert consumer._last_rebootstrap_mono == before


def test_consumer_close_is_idempotent(consumer):
    consumer.close()
    consumer.close()


def test_subscriber_delivers_messages_via_callback(subscriber):
    stub = subscriber.consumer._consumer
    stub.create_topic("topic", num_partitions=1)
    stub.add_message("topic", 0, offset=0, key=b"k", value=b"A")
    stub.add_message("topic", 0, offset=1, key=b"k", value=b"B")

    delivered = []
    calls_idle = {"n": 0}

    def on_msgs(items):
        delivered.extend(items)

    def on_idle():
        calls_idle["n"] += 1

    subscriber.subscribe(["topic"], on_msgs, on_idle)
    pump(subscriber, steps=20)

    assert [v for (_, v) in delivered] == [b"A", b"B"]
    assert calls_idle["n"] >= 0


def test_rebootstrap_sets_pending_reassign_when_topics_missing(consumer):
    consumer._topics = ["missing"]
    consumer._pending_reassign = False
    reasons = []
    consumer._on_rebootstrap = reasons.append
    before = consumer._last_rebootstrap_mono
    consumer.rebootstrap("test_missing")
    assert consumer._pending_reassign is True
    assert consumer._last_rebootstrap_mono > before
    assert "test_missing" in reasons


def test_subscriber_recovers_after_failed_rebootstrap_then_reassigns(subscriber, clock):
    # Start with a valid subscription
    initial_stub = subscriber.consumer._consumer
    initial_stub.create_topic("t", num_partitions=1)
    delivered = []
    subscriber.subscribe(["t"], lambda items: delivered.extend(items))

    # Remove topic so rebootstrap fails to re-subscribe
    initial_stub._metadata.topics.pop("t", None)

    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.01)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.01)
    # Force the no-stats watchdog to trigger:
    c._health.last_stats_mono = clock.now() - (subscriber._no_stats_secs + 0.1)
    c._pending_reassign = False

    reasons = []
    c._on_rebootstrap = reasons.append

    # First tick triggers reboot; re-subscribe fails -> pending_reassign=True
    subscriber.tick()
    assert "no_stats_heartbeat" in reasons
    assert c._pending_reassign is True

    # After rebootstrap the underlying stub instance is NEW
    new_stub = subscriber.consumer._consumer
    new_stub.create_topic("t", num_partitions=1)
    new_stub.add_message("t", 0, offset=0, key=b"k", value=b"A")
    new_stub.add_message("t", 0, offset=1, key=b"k", value=b"B")

    # Next ticks will try_reassign() and then deliver
    pump(subscriber, steps=10)
    assert [v for (_, v) in delivered] == [b"A", b"B"]



def test_watchdog_reboots_on_no_stats_heartbeat(subscriber, clock):
    stub = subscriber.consumer._consumer
    stub.create_topic("x", num_partitions=1)

    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append

    subscriber.subscribe(["x"], lambda _: None)

    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.01)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.01)
    c._health.last_stats_mono = clock.now() - (subscriber._no_stats_secs + 0.01)
    c._pending_reassign = False

    subscriber.tick()  # should trigger
    assert "no_stats_heartbeat" in reasons


def test_watchdog_reboots_on_all_brokers_down(subscriber, clock):
    stub = subscriber.consumer._consumer
    stub.create_topic("x", num_partitions=1)

    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append

    subscriber.subscribe(["x"], lambda _: None)

    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.01)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.01)
    c._health.all_down_since = clock.now() - (subscriber._all_down_secs + 0.01)
    c._pending_reassign = False

    subscriber.tick()
    assert "all_brokers_down" in reasons


def test_watchdog_respects_reboot_cooldown(subscriber, clock):
    stub = subscriber.consumer._consumer
    stub.create_topic("x", num_partitions=1)

    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append

    subscriber.subscribe(["x"], lambda _: None)

    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.01)
    c._last_rebootstrap_mono = clock.now()  # cooldown NOT satisfied
    c._health.last_stats_mono = clock.now() - (subscriber._no_stats_secs + 0.01)
    c._pending_reassign = False

    # Should NOT reboot yet (cooldown not satisfied)
    subscriber.tick()
    assert reasons == []

    # Advance past cooldown and try again -> should reboot
    clock.sleep(subscriber._cooldown_secs + 0.1)
    subscriber.tick()
    assert "no_stats_heartbeat" in reasons


def test_stuck_with_lag_does_not_trigger_for_small_lag(subscriber, clock):
    """
    Simulate a stall with lag=1; watchdog should NOT trigger because min_lag_for_stuck=0.
    Also keep stats "fresh" so the no-stats watchdog doesn't preempt this scenario.
    """
    # Set up topic and subscribe
    stub = subscriber.consumer._consumer
    stub.create_topic("s", num_partitions=1)
    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append
    subscriber.subscribe(["s"], lambda _: None)

    # Satisfy grace & cooldown; refresh stats so no-stats doesn't trigger
    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.05)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.05)
    c._health.last_stats_mono = clock.now()

    # add no messages -> lag = 0 < min_lag_for_stuck(=1)

    # Simulate consumer stall: no deliveries even though lag exists
    # by overriding the inner stub's consume to always return []
    orig_consume = stub.consume
    stub.consume = lambda num_messages, timeout=None: []

    # Wait longer than stuck_with_lag_secs
    clock.sleep(subscriber._stuck_with_lag_secs + 0.2)

    # Refresh stats so no-stats watchdog doesn't preempt
    c._health.last_stats_mono = clock.now()

    # Tick -> should NOT reboot because lag=0 < min_lag_for_stuck(=1)
    subscriber.tick()
    assert "stuck_no_progress_despite_lag" not in reasons

    # Restore
    stub.consume = orig_consume


def test_stuck_with_lag_triggers_rebootstrap_when_lag_high_and_no_progress(subscriber, clock):
    """
    Simulate a stall with lag>=1 and no deliveries for > stuck_with_lag_secs; must reboot.
    Keep stats fresh so the stuck watchdog fires first.
    """
    # Set up topic and subscribe
    stub = subscriber.consumer._consumer
    stub.create_topic("s", num_partitions=1)
    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append
    subscriber.subscribe(["s"], lambda _: None)

    # Satisfy grace & cooldown; refresh stats so no-stats doesn't trigger
    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.05)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.05)
    c._health.last_stats_mono = clock.now()

    # Add >=1 messages so lag >= 1
    stub.add_message("s", 0, offset=0, key=b"k", value=b"A")

    # Simulate consumer stall (consume returns nothing even if messages exist)
    orig_consume = stub.consume
    stub.consume = lambda num_messages, timeout=None: []

    # No deliveries happen -> last_deliver_mono stays at subscribe time
    clock.sleep(subscriber._stuck_with_lag_secs + 0.2)

    # Refresh stats right before tick so no-stats watchdog doesn't preempt
    c._health.last_stats_mono = clock.now()

    # Tick -> should trigger stuck watchdog
    subscriber.tick()
    assert "stuck_no_progress_despite_lag" in reasons

    # Clean up
    stub.consume = orig_consume


def test_stuck_with_lag_ignored_until_grace_and_cooldown(subscriber, clock):
    """
    Ensure we don't trigger the stuck watchdog before wait_after_assign or cooldown are satisfied.
    Keep stats fresh to avoid the no-stats watchdog.
    """
    stub = subscriber.consumer._consumer
    stub.create_topic("s", num_partitions=1)
    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append
    subscriber.subscribe(["s"], lambda _: None)

    c = subscriber.consumer

    # For this test, make grace & cooldown larger than the stuck window,
    # so we can pass the stuck window WITHOUT satisfying grace/cooldown.
    subscriber._wait_after_assign_secs = 5.0
    subscriber._cooldown_secs = 5.0

    # Set "start" points for the larger thresholds
    c._last_assign_mono = clock.now()
    c._last_rebootstrap_mono = clock.now()
    c._health.last_stats_mono = clock.now()  # keep stats fresh

    # Add >=1 messages -> lag >= 1 (so stuck-with-lag condition is potentially active)
    stub.add_message("s", 0, offset=0, key=b"k", value=b"A")

    # Stall consume
    orig_consume = stub.consume
    stub.consume = lambda num_messages, timeout=None: []

    # Advance past the stuck window but NOT the (now larger) grace/cooldown
    clock.sleep(subscriber._stuck_with_lag_secs + 0.5)  # ~1.3s < 5s
    c._health.last_stats_mono = clock.now()  # keep stats fresh
    subscriber.tick()

    # Stuck should NOT trigger yet because grace/cooldown are not satisfied
    assert "stuck_no_progress_despite_lag" not in reasons

    # Now satisfy grace & cooldown and tick again -> should trigger stuck watchdog
    clock.sleep(subscriber._wait_after_assign_secs + 0.1)  # pass 5s window
    c._health.last_stats_mono = clock.now()  # keep stats fresh
    subscriber.tick()
    assert "stuck_no_progress_despite_lag" in reasons

    stub.consume = orig_consume

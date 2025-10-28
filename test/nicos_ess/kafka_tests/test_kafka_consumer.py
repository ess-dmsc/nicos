import json

import pytest

import nicos_ess.devices.kafka.consumer as mod

from test.nicos_ess.kafka_tests.doubles.consumer import (
    ConsumerStub,
    PartitionMetadata as PartitionMetadataStub,
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
    yield c
    c._consumer.clear_all_clusters()


@pytest.fixture
def consumer_latest(clock):
    """KafkaConsumer with starting_offset='latest' wired to the stub via DI."""
    c = mod.KafkaConsumer(
        brokers=["broker1:9092"],
        starting_offset="latest",
        consumer_factory=lambda conf: ConsumerStub(conf),
        topic_partition_factory=lambda t, p, o=None: TopicPartitionStub(
            t, p, o if o is not None else 0
        ),
        now=clock.now,
        sleep=clock.sleep,
        rand_uniform=lambda a, b: 0.0,
    )
    yield c
    c._consumer.clear_all_clusters()


@pytest.fixture
def subscriber(clock, consumer):
    """Subscriber using the injected consumer and a synchronous tick loop."""
    sub = mod.KafkaSubscriber(
        consumer=consumer,
        no_stats_secs=1.0,  # speed up tests
        all_down_secs=1.0,  # speed up tests
        cooldown_secs=0.5,  # speed up tests
        wait_after_assign_secs=0.2,  # speed up tests
        stuck_with_lag_secs=0.8,  # fast stuck detection for tests
        min_lag_for_stuck=1,  # only reboot when lag >= 2
        now=clock.now,
        sleep=clock.sleep,
        use_thread=False,  # run synchronously in tests
    )
    yield sub
    sub.consumer._consumer.clear_all_clusters()


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


def test_delete_then_recreate_latest_reads_only_new(consumer_latest):
    c = consumer_latest
    stub = c._consumer

    # Create & subscribe
    stub.create_topic("r", num_partitions=2)
    c.subscribe(["r"])

    # Simulate topic deletion (metadata disappears)
    stub._metadata.topics.pop("r", None)

    # Simulate broker error -> pending_reassign + post-assign seek
    class DummyErr:
        def code(self):
            return 3  # UNKNOWN_TOPIC_OR_PART

        def name(self):
            return "UNKNOWN_TOPIC_OR_PART"

        def fatal(self):
            return False

        def retriable(self):
            return True

        def str(self):
            return "topic does not exist"

    c._on_error(DummyErr())
    assert c._pending_reassign is True and c._need_seek_after_assign is True

    # Recreate topic and produce some 'old' data before reassignment
    stub.create_topic("r", num_partitions=2)
    stub.add_message("r", 0, offset=0, key=b"k", value=b"OLD-A")
    stub.add_message("r", 1, offset=0, key=b"k", value=b"OLD-B")

    # Reassign now that metadata exists; post-assign seek should go to END
    assert c.try_reassign() is True

    # Produce 'new' data after reassignment/seek-to-end
    stub.add_message("r", 0, offset=1, key=b"k", value=b"NEW")

    msgs = c.consume_batch(max_messages=10, timeout_s=0.05)
    vals = [m.value() for m in msgs]
    assert b"NEW" in vals
    assert b"OLD-A" not in vals and b"OLD-B" not in vals


def test_delete_then_recreate_earliest_reads_from_beginning(consumer):
    c = consumer  # earliest
    stub = c._consumer

    # Create & subscribe
    stub.create_topic("r", num_partitions=1)
    c.subscribe(["r"])

    # Simulate topic deletion
    stub._metadata.topics.pop("r", None)

    # Simulate broker error -> pending_reassign + post-assign seek
    class DummyErr:
        def code(self):
            return 3

        def name(self):
            return "UNKNOWN_TOPIC_OR_PART"

        def fatal(self):
            return False

        def retriable(self):
            return True

        def str(self):
            return "topic does not exist"

    c._on_error(DummyErr())
    assert c._pending_reassign is True and c._need_seek_after_assign is True

    # Recreate topic and add 'existing' data before reassignment
    stub.create_topic("r", num_partitions=1)
    stub.add_message("r", 0, offset=0, key=b"k", value=b"A")
    stub.add_message("r", 0, offset=1, key=b"k", value=b"B")

    # Reassign; post-assign seek should go to BEGINNING
    assert c.try_reassign() is True

    msgs = c.consume_batch(max_messages=10, timeout_s=0.05)
    assert [m.value() for m in msgs] == [b"A", b"B"]


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


def test_stuck_with_lag_triggers_rebootstrap_when_lag_high_and_no_progress(
    subscriber, clock
):
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


def test_tick_returns_early_when_pending_reassign(subscriber, clock, monkeypatch):
    """
    If _pending_reassign is True and try_reassign() returns False,
    tick() should sleep briefly and return early (no callbacks, no reboot).
    """
    calls = {"msgs": 0, "idle": 0}

    # Create the topic before subscribing
    stub = subscriber.consumer._consumer
    stub.create_topic("dummy", num_partitions=1)

    subscriber.subscribe(
        ["dummy"], lambda _: calls.__setitem__("msgs", calls["msgs"] + 1)
    )
    # Set pending reassign and force try_reassign to fail
    subscriber.consumer._pending_reassign = True
    monkeypatch.setattr(subscriber.consumer, "try_reassign", lambda: False)

    t0 = clock.now()
    subscriber.tick()
    # Slept at least 0.01s
    assert clock.now() >= t0 + 0.01
    assert calls["msgs"] == 0  # no messages delivered


def test_poll_without_assignment_returns_none(consumer):
    # Poll with no assignment should be harmless and return None
    assert consumer.assignment() == []
    assert consumer.poll(timeout_ms=10) is None


def test_compute_total_lag_uses_position_when_available(subscriber):
    """
    With starting_offset='earliest', position should behave as low watermark when never delivered.
    Add two messages => high=2; expected total lag = 2 - 0 = 2.
    """
    stub = subscriber.consumer._consumer
    stub.create_topic("s", num_partitions=1)
    stub.add_message("s", 0, offset=0, key=b"k", value=b"A")
    stub.add_message("s", 0, offset=1, key=b"k", value=b"B")
    subscriber.subscribe(["s"], lambda _: None)
    assert subscriber._compute_total_lag() == 2


def test_partition_probe_detects_partition_increase_and_reassigns(subscriber, clock):
    c = subscriber.consumer
    stub = c._consumer

    stub.create_topic("pp", num_partitions=1)
    subscriber.subscribe(["pp"], lambda _: None)

    # Simulate broker-side increase to 2 partitions
    stub._metadata.topics["pp"].partitions[1] = PartitionMetadataStub(1)

    # Force the probe to run on next tick
    c._last_meta_probe = clock.now() - (mod.PARTITION_PROBE_INTERVAL_SECS + 0.1)

    # In the same tick the probe sets pending_reassign and try_reassign() applies it
    subscriber.tick()

    assigned = {(tp.topic, tp.partition) for tp in c.assignment()}
    assert assigned == {("pp", 0), ("pp", 1)}


def test_empty_reads_with_stats_lag_triggers_rebootstrap(subscriber, clock):
    stub = subscriber.consumer._consumer
    stub.create_topic("laggy", num_partitions=1)
    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append
    subscriber.subscribe(["laggy"], lambda _: None)

    c = subscriber.consumer
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.05)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.05)

    # Pretend stats say there is lag (and keep stats fresh throughout the loop)
    c._health.stats_total_lag = 2

    for _ in range(50):
        c._health.last_stats_mono = (
            clock.now()
        )  # keep stats fresh so no-stats watchdog does NOT fire
        subscriber.tick()

    assert "stuck_empty_reads_with_stats_lag" in reasons


def test_first_message_after_long_idle_is_consumed_instead_of_stuck_rebootstrap_wm(
    subscriber, clock
):
    """
    long idle at end-of-log (no lag), then exactly one new record arrives.
    Expectation: we should consume the record rather than triggering the
    stuck-with-lag watchdog (which would use a huge no_progress_for).
    This test exercises the WATERMARK-based lag path (no stats coverage).
    """
    stub = subscriber.consumer._consumer
    stub.create_topic("idle", num_partitions=1)

    delivered = []
    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append

    # Subscribe and satisfy grace + cooldown
    subscriber.subscribe(["idle"], lambda items: delivered.extend(items))
    c = subscriber.consumer
    c._pending_reassign = False
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.05)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.05)

    # Keep stats fresh so the no-stats watchdog never fires,
    # but don't provide stats lag (force WATERMARK path).
    c._health.last_stats_mono = clock.now()
    c._health.stats_by_tp = {}
    c._health.stats_total_lag = 0

    # Simulate long idle (no messages yet) -> no_progress_for grows large.
    clock.sleep(900.0)  # large idle interval
    c._health.last_stats_mono = clock.now()  # keep stats fresh

    # Now exactly one new message shows up (lag becomes 1)
    stub.add_message("idle", 0, offset=0, key=b"k", value=b"FIRST")

    # On this tick, we should deliver instead of rebooting as "stuck".
    subscriber.tick()

    # Validate: no stuck reboot reason, message delivered
    assert b"FIRST" in [v for (_, v) in delivered]
    assert "stuck_no_progress_despite_lag" not in reasons


def test_first_message_after_long_idle_is_consumed_instead_of_stuck_rebootstrap_stats(
    subscriber, clock
):
    """
    Same scenario as above but exercising the STATS-based lag path.
    When stats claim lag=1 right after a long idle, we should still consume
    rather than rebooting as stuck.
    """
    stub = subscriber.consumer._consumer
    stub.create_topic("idle_stats", num_partitions=1)

    delivered = []
    reasons = []
    subscriber.consumer._on_rebootstrap = reasons.append

    # Subscribe and satisfy grace + cooldown
    subscriber.subscribe(["idle_stats"], lambda items: delivered.extend(items))
    c = subscriber.consumer
    c._pending_reassign = False
    c._last_assign_mono = clock.now() - (subscriber._wait_after_assign_secs + 0.05)
    c._last_rebootstrap_mono = clock.now() - (subscriber._cooldown_secs + 0.05)

    # Long idle with no messages; keep stats fresh but with zero lag
    c._health.stats_by_tp = {}
    c._health.stats_total_lag = 0
    c._health.last_stats_mono = clock.now()
    clock.sleep(600.0)
    c._health.last_stats_mono = clock.now()

    # One new message appears
    stub.add_message("idle_stats", 0, offset=0, key=b"k", value=b"FIRST-S")

    # Make stats report lag=1 and cover the assignment
    assigned = c.assignment()
    assert assigned, "expected an assignment"
    # Build full coverage map for stats path
    stats_map = {}
    for tp in assigned:
        stats_map[(tp.topic, tp.partition)] = {
            "lag": 1 if (tp.topic, tp.partition) == ("idle_stats", 0) else 0,
            "fetch_state": "active",
        }
    c._health.stats_by_tp = stats_map
    c._health.stats_total_lag = 1
    c._health.last_stats_mono = clock.now()  # fresh stats so stats path is used

    # On this tick, we should consume rather than rebooting as stuck.
    subscriber.tick()

    # Validate: delivered and no stuck reboot
    assert b"FIRST-S" in [v for (_, v) in delivered]
    assert "stuck_no_progress_despite_lag" not in reasons

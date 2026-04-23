# ruff: noqa: E402
from unittest import TestCase

import pytest

pytest.importorskip("confluent_kafka")
pytest.importorskip("streaming_data_types")

from streaming_data_types.logdata_f144 import serialise_f144

from nicos_ess.devices.kafka import readback

from test.nicos_ess.test_devices.doubles.kafka_stubs import StubKafkaSubscriber

LOW_LEVEL_SETUP = "ess_kafka_readback_lowlevel"
FIRST_SETUP = "ess_kafka_readback_first"
SECOND_SETUP = "ess_kafka_readback_second"

TOPIC_1 = "topic1"
TOPIC_2 = "topic2"
TOPIC_3 = "topic3"

FIRST_TOPIC_1_SOURCE = "src:first:topic1"
FIRST_TOPIC_2_SOURCE = "src:first:topic2"
SECOND_TOPIC_1_SOURCE = "src:second:topic1"
SECOND_TOPIC_3_SOURCE = "src:second:topic3"

# Set to None because we load the setup after the mocks are in place.
session_setup = None


@pytest.fixture
def kafka_readback_stubs(monkeypatch):
    subscribers = []

    def create_subscriber(*args, **kwargs):
        subscriber = StubKafkaSubscriber(*args, **kwargs)
        subscribers.append(subscriber)
        return subscriber

    monkeypatch.setattr(readback, "KafkaSubscriber", create_subscriber)
    return subscribers


def emit_readback_messages(subscribers, *payloads, topic):
    subscriber = next(
        subscriber
        for subscriber in subscribers
        if subscriber.subscribed and subscriber.subscribed[-1] == [topic]
    )
    batch = [((0, 0), payload) for payload in payloads]
    subscriber.emit_messages(batch)


class TestKafkaReadbackSmoke(TestCase):
    @pytest.fixture(autouse=True)
    def prepare(self, session, kafka_readback_stubs):
        self.session = session
        self.kafka_readback_stubs = kafka_readback_stubs
        self.session.unloadSetup()
        yield
        self.session.unloadSetup()

    def test_loading_readables_auto_loads_shared_router_and_fans_out_updates(
        self,
    ):
        self.session.loadSetup(FIRST_SETUP, {})

        assert FIRST_SETUP in self.session.loaded_setups
        assert LOW_LEVEL_SETUP in self.session.loaded_setups
        assert FIRST_SETUP in self.session.explicit_setups
        assert LOW_LEVEL_SETUP not in self.session.explicit_setups

        first_topic_1 = self.session.getDevice("FirstTopic1Readable")
        first_topic_2 = self.session.getDevice("FirstTopic2Readable")
        router = self.session.getDevice("KafkaReadbacks")

        assert first_topic_1._attached_kafka is router
        assert first_topic_2._attached_kafka is router
        assert len(self.kafka_readback_stubs) == 3
        assert all(
            subscriber.brokers == ["localhost:9092"]
            for subscriber in self.kafka_readback_stubs
        )
        assert [subscriber.subscribed for subscriber in self.kafka_readback_stubs] == [
            [[TOPIC_1]],
            [[TOPIC_2]],
            [[TOPIC_3]],
        ]

        self.session.loadSetup(SECOND_SETUP, {})

        assert SECOND_SETUP in self.session.loaded_setups
        assert SECOND_SETUP in self.session.explicit_setups
        assert LOW_LEVEL_SETUP in self.session.loaded_setups
        assert LOW_LEVEL_SETUP not in self.session.explicit_setups

        second_topic_1 = self.session.getDevice("SecondTopic1Readable")
        second_topic_3 = self.session.getDevice("SecondTopic3Readable")

        assert second_topic_1._attached_kafka is router
        assert second_topic_3._attached_kafka is router
        assert len(self.kafka_readback_stubs) == 3

        emit_readback_messages(
            self.kafka_readback_stubs,
            serialise_f144(FIRST_TOPIC_1_SOURCE, 1.5, 1_000_000_000),
            serialise_f144(SECOND_TOPIC_1_SOURCE, 2.5, 2_000_000_000),
            topic=TOPIC_1,
        )
        emit_readback_messages(
            self.kafka_readback_stubs,
            serialise_f144(FIRST_TOPIC_2_SOURCE, 3.5, 3_000_000_000),
            topic=TOPIC_2,
        )
        emit_readback_messages(
            self.kafka_readback_stubs,
            serialise_f144(SECOND_TOPIC_3_SOURCE, 4.5, 4_000_000_000),
            topic=TOPIC_3,
        )

        assert first_topic_1.read() == pytest.approx(1.5)
        assert first_topic_2.read() == pytest.approx(3.5)
        assert second_topic_1.read() == pytest.approx(2.5)
        assert second_topic_3.read() == pytest.approx(4.5)

        emit_readback_messages(
            self.kafka_readback_stubs,
            serialise_f144(FIRST_TOPIC_1_SOURCE, 5.5, 5_000_000_000),
            topic=TOPIC_1,
        )

        assert first_topic_1.read() == pytest.approx(5.5)
        assert first_topic_2.read() == pytest.approx(3.5)
        assert second_topic_1.read() == pytest.approx(2.5)
        assert second_topic_3.read() == pytest.approx(4.5)

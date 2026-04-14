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

READBACK_TOPIC = "readbacks"
FIRST_SOURCE = "src:first"
SECOND_SOURCE = "src:second"

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


def emit_readback_messages(subscribers, *payloads, topic=READBACK_TOPIC):
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

    def test_loading_readables_auto_loads_shared_consumer_and_fans_out_updates(
        self,
    ):
        self.session.loadSetup(FIRST_SETUP, {})

        assert FIRST_SETUP in self.session.loaded_setups
        assert LOW_LEVEL_SETUP in self.session.loaded_setups
        assert FIRST_SETUP in self.session.explicit_setups
        assert LOW_LEVEL_SETUP not in self.session.explicit_setups

        first = self.session.getDevice("FirstKafkaReadable")
        consumer = self.session.getDevice("KafkaReadbacks")

        assert first._attached_kafka is consumer
        assert len(self.kafka_readback_stubs) == 1
        assert self.kafka_readback_stubs[0].brokers == ["localhost:9092"]
        assert self.kafka_readback_stubs[0].subscribed == [[READBACK_TOPIC]]

        self.session.loadSetup(SECOND_SETUP, {})

        assert SECOND_SETUP in self.session.loaded_setups
        assert SECOND_SETUP in self.session.explicit_setups
        assert LOW_LEVEL_SETUP in self.session.loaded_setups
        assert LOW_LEVEL_SETUP not in self.session.explicit_setups

        second = self.session.getDevice("SecondKafkaReadable")

        assert second._attached_kafka is consumer
        assert len(self.kafka_readback_stubs) == 1

        emit_readback_messages(
            self.kafka_readback_stubs,
            serialise_f144(FIRST_SOURCE, 1.5, 1_000_000_000),
            serialise_f144(SECOND_SOURCE, 2.5, 2_000_000_000),
        )

        assert first.read() == pytest.approx(1.5)
        assert second.read() == pytest.approx(2.5)

        emit_readback_messages(
            self.kafka_readback_stubs,
            serialise_f144(FIRST_SOURCE, 3.5, 3_000_000_000),
        )

        assert first.read() == pytest.approx(3.5)
        assert second.read() == pytest.approx(2.5)

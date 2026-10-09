import pytest
from confluent_kafka import KafkaException

from nicos.utils import formatExtendedTraceback
from nicos_ess.devices.kafka import consumer, producer
from nicos_ess.devices.kafka.utils import SecretStr, reveal_secrets

PASSWORD = "hunter2hunter2"


def test_secret_str_hides_its_value():
    secret = SecretStr(PASSWORD)

    assert PASSWORD not in f"{secret} {secret!r} {[secret]} { ({'key': secret}) }"
    assert secret.get_secret_value() == PASSWORD


def test_reveal_secrets_only_touches_secrets():
    config = {"sasl.username": "user", "sasl.password": SecretStr(PASSWORD)}

    assert reveal_secrets(config) == {
        "sasl.username": "user",
        "sasl.password": PASSWORD,
    }


@pytest.mark.parametrize(
    "module, create",
    [
        (consumer, lambda: consumer.KafkaConsumer.create(["localhost:9092"])),
        (producer, lambda: producer.KafkaProducer.create(["localhost:9092"])),
    ],
    ids=["consumer", "producer"],
)
def test_failing_client_creation_does_not_log_the_password(monkeypatch, module, create):
    sasl_config = {
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "SCRAM-SHA-256",
        "sasl.username": "user",
        "sasl.password": SecretStr(PASSWORD),
        "ssl.ca.location": "/nonexistent/ca.crt",
    }
    monkeypatch.setattr(module, "create_sasl_config", lambda: sasl_config)

    with pytest.raises(KafkaException) as excinfo:
        create()

    assert PASSWORD not in formatExtendedTraceback(excinfo.value)

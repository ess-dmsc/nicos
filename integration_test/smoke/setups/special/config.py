import os

description = "High-level configuration settings for smoke integration tests"

group = "configdata"

CACHE_HOST = os.environ["NICOS_SMOKE_CACHE_HOST"]
DAEMON_HOST = os.environ["NICOS_SMOKE_DAEMON_HOST"]


def _kafka_brokers():
    return [
        entry.strip()
        for entry in os.environ["NICOS_SMOKE_KAFKA_BOOTSTRAP"].split(",")
        if entry.strip()
    ]


KAFKA_BROKERS = _kafka_brokers()

FORWARDER_STATUS_TOPIC = ["test_smoke_forwarder_dynamic_status"]
FORWARDER_CONFIG_TOPIC = "test_smoke_forwarder_dynamic_config"

FILEWRITER_POOL_TOPIC = os.environ["NICOS_SMOKE_FILEWRITER_POOL_TOPIC"]
FILEWRITER_STATUS_TOPICS = [
    os.environ["NICOS_SMOKE_FILEWRITER_INSTRUMENT_TOPIC"],
    os.environ["NICOS_SMOKE_FILEWRITER_STATUS_TOPIC"],
]
FILEWRITER_INSTRUMENT_TOPIC = os.environ["NICOS_SMOKE_FILEWRITER_INSTRUMENT_TOPIC"]

SCICHAT_TOPIC = "test_smoke_scichat"
COLLECTOR_OUTPUT_TOPIC = "test_smoke_nicos_devices"

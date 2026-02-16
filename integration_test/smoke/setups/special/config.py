description = "High-level configuration settings for smoke integration tests"

group = "configdata"

CACHE_HOST = "localhost:24869"
DAEMON_HOST = "localhost:21301"

KAFKA_BROKERS = ["localhost:19092"]

FORWARDER_STATUS_TOPIC = ["test_smoke_forwarder_dynamic_status"]
FORWARDER_CONFIG_TOPIC = "test_smoke_forwarder_dynamic_config"

FILEWRITER_STATUS_TOPICS = ["test_smoke_filewriter", "test_smoke_filewriter_status"]
FILEWRITER_POOL_TOPIC = "test_smoke_filewriter_pool"
FILEWRITER_INSTRUMENT_TOPIC = "test_smoke_filewriter"

SCICHAT_TOPIC = "test_smoke_scichat"
COLLECTOR_OUTPUT_TOPIC = "test_smoke_nicos_devices"

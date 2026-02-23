description = "setup for the NICOS collector (smoke integration)"
group = "special"

devices = dict(
    CacheKafka=device(
        "nicos_ess.devices.cache_kafka_forwarder.CacheKafkaForwarder",
        dev_ignore=["space", "sample"],
        brokers=configdata("config.KAFKA_BROKERS"),
        output_topic=configdata("config.COLLECTOR_OUTPUT_TOPIC"),
    ),
    Collector=device(
        "nicos.services.collector.Collector",
        cache=configdata("config.CACHE_HOST"),
        forwarders=["CacheKafka"],
    ),
)

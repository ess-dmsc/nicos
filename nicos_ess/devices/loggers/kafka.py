"""Kafka log handler"""

import logging
import urllib


def create_kafka_logging_handler(config):
    from nicos.core import ConfigurationError

    try:
        from kafka_logger.handlers import KafkaLoggingHandler

        if hasattr(config, "kafka_logger"):
            url = urllib.parse.urlparse(config.kafka_logger)
            if not url.netloc or not url.path[1:]:
                raise ConfigurationError("kafka_logger: invalid url")
            kafka_handler = KafkaLoggingHandler(
                url.netloc,
                url.path[1:],
                security_protocol="PLAINTEXT",
            )
            kafka_handler.setLevel(logging.WARNING)
            return kafka_handler

    except ImportError:
        return

import os

from nicos.core import ConfigurationError
from nicos.utils.credentials.keystore import nicoskeystore


def create_sasl_config():
    """Create a SASL config for connecting to Kafka.

    Note that whereas some SASL mechanisms do not require user/password, the
    three we currently support do.

    :return: A dictionary of configuration parameters.
    """
    protocol = os.environ.get("KAFKA_SSL_PROTOCOL")
    if not protocol:
        return {}

    mechanism = os.environ.get("KAFKA_SSL_MECHANISM")
    cert_filepath = os.environ.get("KAFKA_CERT_PATH")
    username = os.environ.get("KAFKA_USER")
    password = nicoskeystore.getCredential("kafka_auth")

    supported_security_protocols = ["SASL_PLAINTEXT", "SASL_SSL"]
    supported_sasl_mechanisms = ["PLAIN", "SCRAM-SHA-512", "SCRAM-SHA-256"]

    if protocol not in supported_security_protocols:
        raise ConfigurationError(
            f"Security protocol {protocol} not supported, use one of "
            f"{supported_security_protocols}"
        )

    if not mechanism:
        raise ConfigurationError(
            f"SASL mechanism must be specified for security protocol {protocol}"
        )
    elif mechanism not in supported_sasl_mechanisms:
        raise ConfigurationError(
            f"SASL mechanism {mechanism} not supported, use one of "
            f"{supported_sasl_mechanisms}"
        )

    if not username or not password:
        raise ConfigurationError(
            f"Username and password must be provided to use SASL {mechanism}"
        )

    sasl_config = {
        "security.protocol": protocol,
        "sasl.mechanism": mechanism,
        "sasl.username": username,
        "sasl.password": password,
    }

    if cert_filepath:
        sasl_config["ssl.ca.location"] = cert_filepath

    return sasl_config

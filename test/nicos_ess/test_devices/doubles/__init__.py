"""Reusable doubles for ESS device tests."""

from test.nicos_ess.test_devices.doubles.epics_pva_backend import (
    FakeEpicsBackend,
    analog_moveable_config,
    mapped_config,
    patch_create_wrapper,
    string_moveable_config,
)
from test.nicos_ess.test_devices.doubles.epics_seed import (
    seed_epics_jog_motor_defaults,
)
from test.nicos_ess.test_devices.doubles.harness_devices import (
    HarnessMappedMoveable,
    HarnessMoveable,
    HarnessReadable,
)
from test.nicos_ess.test_devices.doubles.harness_helpers import (
    wait_for,
    wait_until_complete,
)
from test.nicos_ess.test_devices.doubles.kafka_stubs import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
    patch_kafka_stubs,
)
from test.nicos_ess.test_devices.doubles.mapped_controller_devices import (
    HarnessLinearAxis,
    HarnessMoveableNoPrecision,
)

__all__ = [
    "FakeEpicsBackend",
    "HarnessLinearAxis",
    "HarnessMoveableNoPrecision",
    "HarnessMappedMoveable",
    "HarnessMoveable",
    "HarnessReadable",
    "StubKafkaConsumer",
    "StubKafkaProducer",
    "StubKafkaSubscriber",
    "analog_moveable_config",
    "mapped_config",
    "patch_kafka_stubs",
    "patch_create_wrapper",
    "seed_epics_jog_motor_defaults",
    "string_moveable_config",
    "wait_for",
    "wait_until_complete",
]

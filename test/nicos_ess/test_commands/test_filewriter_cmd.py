"""Test the filewriter-related commands."""

import pytest

from nicos_ess.commands.filewriter import nexusfile_open
from nicos_ess.devices.datasinks import file_writer
from nicos_ess.devices.datasinks.nexus_structure import (
    NexusStructureJsonFile,
)
from nicos_ess.devices.kafka import status_handler
from test.nicos_ess.command_helpers import loaded_setup
from test.nicos_ess.test_devices.doubles import (
    StubKafkaConsumer,
    StubKafkaProducer,
    StubKafkaSubscriber,
)

session_setup = None
COUNT_TIMER_PRESET_SECONDS = 0.05
CHANNEL_PRESET_TOTAL = 5


class HarnessNexusStructureProvider(NexusStructureJsonFile):
    def get_structure(self, metainfo, counter):
        del metainfo, counter
        return "{}"


@pytest.fixture
def kafka_stubs(monkeypatch):
    monkeypatch.setattr(status_handler, "KafkaSubscriber", StubKafkaSubscriber)
    monkeypatch.setattr(
        file_writer.KafkaConsumer, "create", lambda *args, **kwargs: StubKafkaConsumer()
    )
    monkeypatch.setattr(
        file_writer.KafkaProducer, "create", lambda *args, **kwargs: StubKafkaProducer()
    )


@pytest.fixture
def filewriter_control_sink_devices(device_harness, kafka_stubs):
    # kafka stubs not used directly but needed to create filewriter devices
    del kafka_stubs

    with device_harness.activate("daemon") as daemon_session:
        daemon_session.experiment.propinfo["proposal"] = "123456"
        daemon_session.experiment.run_title = "mocksessionexp_runtitle"
    # attached filewriter status device
    device_harness.create_pair(
        file_writer.FileWriterStatus,
        name="filewriter_status_device",
        shared={
            "brokers": ["localhost:9092"],
            "statustopic": ["filewriter_status"],
        },
    )
    # attached nexus structure device
    device_harness.create_pair(
        HarnessNexusStructureProvider,
        name="NexusStructure",
        shared={
            "instrument_name": "ymir",
        },
    )
    return device_harness.create_pair(
        file_writer.FileWriterControlSink,
        name="file_writer_control_sink",
        shared={
            "brokers": ["localhost:9092"],
            "pool_topic": "filewriter_pool",
            "instrument_topic": "filewriter_instrument",
            "status": "filewriter_status_device",
            "nexus": "NexusStructure",
        },
    )


def test_nexusfile_open_produces_traceback_log_when_propsalnumber_missing(
    session, device_harness, filewriter_control_sink_devices, caplog
):
    with loaded_setup(session, "ess_filewriter"):
        daemon_device, poller_device = filewriter_control_sink_devices

        assert daemon_device is not None
        assert poller_device is not None

        with device_harness.activate("daemon") as daemon_session:
            daemon_session.experiment.propinfo["proposal"] = None

            with (
                pytest.raises(RuntimeError, match="generator didn't yield"),
                nexusfile_open(),
            ):
                pass
        # Look for an error message in the logs; the NICOS 'log'
        # fixture/TestLogHandler does not work here, as it only picks up the
        # setup phase of the harness for some reason.
        msg = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(msg) == 1
        assert msg[0].exc_info, "Error log record has no traceback information"
        assert isinstance(msg[0].exc_info[1], RuntimeError), (
            "Error log record is missing exception"
        )

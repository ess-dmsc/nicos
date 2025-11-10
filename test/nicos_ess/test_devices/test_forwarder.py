# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Michele Brambilla <michele.brambilla@psi.ch>
#
# *****************************************************************************

import json
import random
import time
from os import getpid
from socket import gethostname
from string import ascii_lowercase

import pytest

from streaming_data_types.logdata_f142 import serialise_f142
from streaming_data_types.status_x5f2 import serialise_x5f2
from streaming_data_types.forwarder_config_update_fc00 import deserialise_fc00

from nicos.core import status, POLLER, MAIN, ConfigurationError
from nicos.utils import createThread

from nicos_ess.devices.forwarder import EpicsKafkaForwarder

try:
    from unittest import TestCase, mock
except ImportError:
    pytestmark = pytest.mark.skip("all tests still WIP")


# Set to None because we load the setup after the mocks are in place.
session_setup = None


def create_stream(pv, protocol="ca", topic="TEST_metadata", schema="f142"):
    return {
        "channel_name": pv,
        "protocol": protocol,
        "output_topic": topic,
        "schema": schema,
    }


def create_x5f2_buffer(streams_json, update_interval=5000):
    streams_message = serialise_x5f2(
        "Forwarder",
        "version",
        "abcd-1234",
        gethostname(),
        getpid(),
        update_interval,
        json.dumps(streams_json),
    )
    return streams_message


def random_string(length):
    letters = ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))


def create_random_messages(num_messages, num_pvs=10):
    start = int(1000 * time.time())
    pvs = [random_string(4) for _ in range(num_pvs)]
    streams = {"streams": [create_stream(pv) for pv in pvs]}
    times = [start + random.randint(0, 1000) for _ in range(num_messages)]
    return {t: streams for t in times}


def create_issued_from_messages(messages):
    _, message = sorted(messages, key=lambda m: m[0])[~0]
    streams = message.get("streams", [])
    issued = {}
    for stream in streams:
        issued[stream["channel_name"]] = (
            stream["output_topic"],
            stream["schema"],
        )
    return issued


def create_f142_buffer(value, source_name="mypv"):
    return serialise_f142(value, source_name)


def create_pv_details_from_messages(messages):
    _, message = sorted(messages, key=lambda m: m[0])[~0]
    streams = message.get("streams", [])
    pv_details = {}
    for stream in streams:
        pv_details[stream["channel_name"]] = (
            stream["output_topic"],
            stream["schema"],
        )
    return pv_details


class TestEpicsKafkaForwarderStatus(TestCase):
    def create_patch(self, name):
        patcher = mock.patch(name)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.sessiontype = POLLER
        self.mock = self.create_patch("nicos_ess.devices.kafka.consumer.KafkaConsumer")
        self.mock.return_value.topics.return_value = "TEST_forwarderStatus"
        self.session.unloadSetup()
        self.session.loadSetup("ess_forwarder", {})
        self.device = self.session.getDevice("KafkaForwarder")
        self.device._setROParam("curstatus", (0, ""))
        self.session.loadSetup("ess_motors", {})
        self.motor = self.session.getDevice("motor1")
        yield
        self.motor.values["position"] = 0
        self.motor.values["nexus_config"] = []
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_update_forwarded_pv(self):
        pvname = "mypv"
        message_json = {"streams": [create_stream(pvname)]}
        update_interval = 5000
        message_fb = create_x5f2_buffer(message_json, update_interval)
        with mock.patch.object(
            EpicsKafkaForwarder, "_status_update_callback"
        ) as mock_method:
            self.device.new_messages_callback([(123456, message_fb)])
            mock_method.assert_called_once()
            messages = mock_method.call_args[0]

        message_json.update({"update_interval": update_interval})
        assert messages == ({123456: message_json},)

        self.device.new_messages_callback([(12345, message_fb)])
        assert self.device.forwarded == {pvname}

    def test_update_forwarded_many_pvs(self):
        assert self.device.curstatus == (0, "")
        pvnames = {f"mypv{d}" for d in range(10)}
        message_json = {"streams": [create_stream(pv) for pv in pvnames]}
        message_fb = create_x5f2_buffer(message_json)
        self.device.new_messages_callback([(12345, message_fb)])
        self.device.new_messages_callback([(12345, message_fb)])
        assert self.device.forwarded == pvnames

    def test_update_forwarded_pv_sets_forwarding_status(self):
        assert self.device.curstatus == (0, "")
        pvname = "mypv"
        message_json = {"streams": [create_stream(pvname)]}
        message_fb = create_x5f2_buffer(message_json)
        self.device.new_messages_callback([(12345, message_fb)])
        assert self.device.curstatus == (status.OK, "Forwarding..")

    def test_update_forwarded_many_pvs_set_forwarding_status(self):
        assert self.device.curstatus == (0, "")
        pvnames = {f"mypv{d}" for d in range(10)}
        message_json = {"streams": [create_stream(pv) for pv in pvnames]}
        message_fb = create_x5f2_buffer(message_json)
        self.device.new_messages_callback([(12345, message_fb)])
        assert self.device.curstatus == (status.OK, "Forwarding..")

    def test_empty_message_gives_idle_state(self):
        message_json = {"streams": []}
        message_fb = create_x5f2_buffer(message_json)
        self.device.new_messages_callback([(12345, message_fb)])
        assert not self.device.forwarded
        assert self.device.curstatus == (status.OK, "idle")

    def test_next_update_flatbuffers(self):
        message_json = {"streams": []}
        for update_interval in [1000, 2000]:
            message_fb = create_x5f2_buffer(message_json, update_interval)
            self.device.new_messages_callback([(123456, message_fb)])
            assert self.device.statusinterval == update_interval // 1000

    def test_forwarded_pv(self):
        nx_conf = {
            "group_name": "motor1",
            "nx_class": "NXcollection",
            "units": "mm",
            "suffix": "readback",
            "source_name": "readpv",
            "schema": "f144",
            "topic": "ymir_motion",
            "protocol": "pva",
            "periodic": 1,
            "dataset_type": "nx_log",
        }
        self.motor.nexus_config = [nx_conf]
        self.device._producer = mock.Mock()
        self.device._stop_requested = False
        thread = createThread(
            "forwarder_updater",
            self.device._update_forwarded_pvs
        )
        for _ in range(10):
            if self.device._producer.produce.called:
                break
            time.sleep(0.1)
        assert self.device._producer.produce.called
        config_topic, buffer = self.device._producer.produce.call_args[0]
        fc = deserialise_fc00(buffer)
        assert fc.streams[0].channel == nx_conf["source_name"]
        assert fc.streams[0].schema == nx_conf["schema"]
        assert fc.streams[0].topic == nx_conf["topic"]


    def test_static_value_to_nexus(self):
        nx_conf = {
            "group_name": "motor1",
            "nx_class": "NXcollection",
            "units": "",
            "suffix": "info",
            "value": "some_value_in_nexus",
            "dataset_type": "static_value",
        }
        self.motor.nexus_config = [nx_conf]
        json_obj = self.device.get_nexus_json()["/entry/instrument"]
        assert json_obj[0]["name"] == nx_conf["group_name"]
        assert json_obj[0]["children"][0]["config"] == {
            "name": f'{nx_conf["group_name"]}_{nx_conf["suffix"]}',
            "values": nx_conf["value"],
            "dtype": "string"
        }

    def test_static_read_to_nexus(self):
        nx_conf = {
            "group_name": "motor1",
            "nx_class": "NXcollection",
            "units": "mm",
            "suffix": "readback",
            "dataset_type": "static_read",
        }
        position = "some_read_string"
        self.motor.nexus_config=[nx_conf]
        self.motor.values["position"] = position
        json_obj = self.device.get_nexus_json()["/entry/instrument"]
        assert json_obj[0]["name"] == nx_conf["group_name"]
        assert json_obj[0]["children"][0]["config"] == {
            "name": f'{nx_conf["group_name"]}_{nx_conf["suffix"]}',
            "values": position,
            "dtype": "string"
        }

    def test_multiple_nexus_config_with_different_paths(self):
        nx_conf1 = {
            "group_name": "motor1",
            "nx_class": "NXcollection",
            "units": "mm",
            "suffix": "readback",
            "dataset_type": "static_read",
            "nexus_path": "/entry/instrument",
        }
        nx_conf2 = {
            "group_name": "motor1",
            "nx_class": "NXcollection",
            "units": "",
            "suffix": "info",
            "value": "some_value_in_nexus",
            "dataset_type": "static_value",
            "nexus_path": "/entry/sample",
        }
        position = 123
        self.motor.nexus_config=[nx_conf1, nx_conf2]
        self.motor.values["position"] = position
        json_by_path = self.device.get_nexus_json()
        assert len(json_by_path) == 2
        json_1 = json_by_path["/entry/instrument"]
        assert json_1[0]["name"] == nx_conf1["group_name"]
        assert json_1[0]["children"][0]["config"] == {
            "name": f'{nx_conf1["group_name"]}_{nx_conf1["suffix"]}',
            "values": position,
            "dtype": "int"
        }
        json_2 = json_by_path["/entry/sample"]
        assert json_2[0]["name"] == nx_conf2["group_name"]
        assert json_2[0]["children"][0]["config"] == {
            "name": f'{nx_conf2["group_name"]}_{nx_conf2["suffix"]}',
            "values": nx_conf2["value"],
            "dtype": "string"
        }

    def test_nexus_config_must_be_list(self):
        bad = {
            "group_name": "motor1",
            "nx_class": "NXcollection",
            "dataset_type": "static_value",
            "value": "ok",
        }  # dict instead of list
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = bad

    def test_nexus_config_items_must_be_dicts(self):
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = ["not-a-dict"]
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [None]

    def test_missing_required_group_name_raises(self):
        bad = {
            "nx_class": "NXcollection",
            "dataset_type": "static_value",
            "value": "X",
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_missing_required_nx_class_raises(self):
        bad = {
            "group_name": "g",
            "dataset_type": "static_value",
            "value": "X",
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_missing_required_dataset_type_raises(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXcollection",
            "value": "X",
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_group_name_and_nx_class_cannot_be_empty(self):
        bad = {"group_name": "", "nx_class": "", "dataset_type": "static_value", "value": "X"}
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_unknown_keys_rejected(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXcollection",
            "dataset_type": "static_value",
            "value": "X",
            "unexpected": 123,
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_invalid_dataset_type_raises(self):
        bad = {"group_name": "g", "nx_class": "NXcollection", "dataset_type": "stream"}
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_static_value_without_value_key_raises(self):
        bad = {"group_name": "g", "nx_class": "NXcollection", "dataset_type": "static_value"}
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_forwarder_keys_present_but_not_nx_log_raises(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "static_read",
            "schema": "f144",
            "topic": "T",
            "source_name": "PV:NAME",
            # protocol/periodic intentionally omitted; still illegal on non-nx_log
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_single_forwarder_key_on_non_nx_log_raises(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "static_read",
            "source_name": "PV:NAME",  # even one key is forbidden unless nx_log
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_forwarder_keys_missing_when_nx_log_raises(self):
        base_missing_topic = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "f144",
            # topic missing -> error
            "source_name": "PV:NAME",
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [base_missing_topic]

        # missing any of the triad must raise
        for missing in ("schema", "topic", "source_name"):
            cfg = {
                "group_name": "g",
                "nx_class": "NXdetector",
                "dataset_type": "nx_log",
                "schema": "f144",
                "topic": "topic",
                "source_name": "PV:NAME",
            }
            cfg.pop(missing)
            with pytest.raises(ConfigurationError):
                self.motor.nexus_config = [cfg]

    def test_forwarder_keys_present_but_empty_raises(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "",
            "topic": "",
            "source_name": "",
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_invalid_protocol_raises_if_provided(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "f144",
            "topic": "topic",
            "source_name": "PV:NAME",
            "protocol": "kafka",  # invalid, must be 'pva' or 'ca'
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

    def test_invalid_periodic_raises_if_provided(self):
        bad = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "f144",
            "topic": "topic",
            "source_name": "PV:NAME",
            "periodic": 2,  # must be 0 or 1 if provided
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad]

        bad2 = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "f144",
            "topic": "topic",
            "source_name": "PV:NAME",
            "periodic": "maybe",
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad2]

    def test_valid_periodic_variants_are_accepted(self):
        ok1 = {
            "group_name": "g",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "f144",
            "topic": "topic",
            "source_name": "PV:NAME",
            "periodic": 0,
        }
        ok2 = dict(ok1, periodic=1)
        ok3 = dict(ok1, periodic=True)  # coerces to 1 in validator, but not defaulted if missing
        ok4 = dict(ok1, periodic=False)  # coerces to 0
        self.motor.nexus_config = [ok1, ok2, ok3, ok4]

    def test_invalid_nexus_path_raises_if_provided(self):
        bad_rel = {
            "group_name": "g",
            "nx_class": "NXcollection",
            "dataset_type": "static_value",
            "value": "X",
            "nexus_path": "entry/instrument",  # not absolute
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad_rel]

        bad_root = {
            "group_name": "g",
            "nx_class": "NXcollection",
            "dataset_type": "static_value",
            "value": "X",
            "nexus_path": "/instrument",  # must start with /entry
        }
        with pytest.raises(ConfigurationError):
            self.motor.nexus_config = [bad_root]

    def test_valid_nx_log_config_minimal_is_accepted(self):
        # protocol/periodic are optional; defaults applied later by forwarder code
        good = {
            "group_name": "det",
            "nx_class": "NXdetector",
            "dataset_type": "nx_log",
            "schema": "f144",
            "topic": "detector-events",
            "source_name": "PV:COUNTS",
        }
        self.motor.nexus_config = [good]

    def test_valid_static_value_minimal_is_accepted(self):
        good = {
            "group_name": "sample",
            "nx_class": "NXsample",
            "dataset_type": "static_value",
            "value": "Ni powder",
        }
        self.motor.nexus_config = [good]
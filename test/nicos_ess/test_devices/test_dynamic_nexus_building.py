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
#   Your Name <you@example.com>
# *****************************************************************************

import json
from pathlib import Path

import pytest

from nicos.core import MAIN, POLLER
from nicos_ess.devices.datasinks.nexus_structure import NexusStructureJsonFile

from nicos_ess.utilities.json_utils import (
    build_named_index_map,
    get_by_named_path,
)

try:
    from unittest import TestCase, mock
except ImportError:
    pytestmark = pytest.mark.skip("all tests still WIP")


# Set to None because we load the setup after the mocks are in place.
session_setup = None


def _minimal_metainfo(counter: int = 1) -> dict:
    """Matches the access pattern in _insert_metadata/_insert_samples."""
    return {
        ("Exp", "run_title"): ["Test run"],
        ("Exp", "proposal"): ["P-001"],
        ("Exp", "title"): ["Beamtime Title"],
        ("Exp", "scripts"): ["import foo\nrun()"],
        ("Exp", "job_id"): "uuid-123",
        ("Exp", "users"): (
            [
                {
                    "name": "John Doe",
                    "email": "",
                    "affiliation": "European Spallation Source ERIC (ESS)",
                    "facility_user_id": "johndoe",
                }
            ],
            "({'name': 'John Doe', 'email': '', 'affiliation': 'European Spallation Source ERIC (ESS)', 'facility_user_id': 'johndoe'})",
            "",
            "experiment",
        ),
        ("Sample", "samples"): [[{"name": "SampleA", "description": "A test sample"}]],
    }


class TestDynamicNexusBuilding(TestCase):
    def create_patch(self, name):
        patcher = mock.patch(name)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        # Ensure relative paths in setups resolve from repo root
        repo_root = Path(__file__).resolve().parents[3]
        monkeypatch.chdir(repo_root)

        self.session = session
        self.session.sessiontype = POLLER

        # Patch KafkaConsumer so loading the forwarder setup doesn't try to connect
        self.kafka_consumer_patch = self.create_patch(
            "nicos_ess.devices.kafka.consumer.KafkaConsumer"
        )
        self.kafka_consumer_patch.return_value.topics.return_value = (
            "TEST_forwarderStatus"
        )

        # Start clean and load the three setups needed for the integrated path:
        # forwarder -> motors -> nexus structure
        self.session.unloadSetup()
        self.session.loadSetup("ess_forwarder", {})
        self.session.loadSetup("ess_motors", {})
        self.session.loadSetup("ess_nexus_structure", {})

        # Devices under test
        self.forwarder = self.session.getDevice("KafkaForwarder")
        self.motor = self.session.getDevice("motor1")
        self.nexus: NexusStructureJsonFile = self.session.getDevice("NexusStructure")
        # Match the setup definition’s alias (if applicable)
        self.nexus.alias = "NexusStructure_Basic"
        # No area-detector placeholder in this test
        self.nexus.area_det_collector_device = ""

        yield

        # Teardown
        self.motor.values["position"] = 0
        self.motor.values["nexus_config"] = []
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_dynamic_build_places_groups_by_path(self):
        """Motor nexus_config → Forwarder get_nexus_json() → NexusStructure insertion under correct paths."""
        # Two entries for the same device, different dataset types & paths
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

        position = 123  # int on purpose (dtype inference should yield "int")
        self.motor.nexus_config = [nx_conf1, nx_conf2]
        self.motor.values["position"] = position

        # Build the final NeXus JSON via the structure device (this will ask the forwarder for by-path groups)
        raw = self.nexus.get_structure(_minimal_metainfo(counter=5), counter=5)
        doc = json.loads(raw)

        # Resolve groups by named path
        path_map = build_named_index_map(doc, include_datasets=True)

        # --- /entry/instrument ---
        instrument = get_by_named_path(doc, path_map, "/entry/instrument")
        assert isinstance(instrument, dict)

        motor_groups_instr = [
            c
            for c in instrument.get("children", [])
            if isinstance(c, dict)
            and c.get("type") == "group"
            and c.get("name") == "motor1"
        ]
        assert motor_groups_instr, "Expected 'motor1' group under /entry/instrument"
        motor1_instr = motor_groups_instr[0]

        datasets_instr = [
            c
            for c in motor1_instr.get("children", [])
            if isinstance(c, dict) and c.get("module") == "dataset"
        ]
        assert datasets_instr, "Expected a dataset under /entry/instrument/motor1"
        ds_instr = datasets_instr[0]
        assert (
            ds_instr["config"]["name"]
            == f'{nx_conf1["group_name"]}_{nx_conf1["suffix"]}'
        )
        assert ds_instr["config"]["values"] == position
        assert ds_instr["config"]["dtype"] == "int"

        # make sure we can also get it by path and that it matches
        motor_groups_instr_by_path = get_by_named_path(
            doc, path_map, "/entry/instrument/motor1"
        )
        assert motor_groups_instr_by_path == motor1_instr

        # --- /entry/sample ---
        sample = get_by_named_path(doc, path_map, "/entry/sample")
        assert isinstance(sample, dict)

        motor_groups_sample = [
            c
            for c in sample.get("children", [])
            if isinstance(c, dict)
            and c.get("type") == "group"
            and c.get("name") == "motor1"
        ]
        assert motor_groups_sample, "Expected 'motor1' group under /entry/sample"
        motor1_sample = motor_groups_sample[0]

        datasets_sample = [
            c
            for c in motor1_sample.get("children", [])
            if isinstance(c, dict) and c.get("module") == "dataset"
        ]
        assert datasets_sample, "Expected a dataset under /entry/sample/motor1"
        ds_sample = datasets_sample[0]
        assert (
            ds_sample["config"]["name"]
            == f'{nx_conf2["group_name"]}_{nx_conf2["suffix"]}'
        )
        assert ds_sample["config"]["values"] == nx_conf2["value"]
        assert ds_sample["config"]["dtype"] == "string"

        # make sure we can also get it by path and that it matches
        motor_groups_sample_by_path = get_by_named_path(
            doc, path_map, "/entry/sample/motor1"
        )
        assert motor_groups_sample_by_path == motor1_sample

        # try reading sample name and description inserted by nexus structure
        sample_name_ds = get_by_named_path(doc, path_map, "/entry/sample/name")
        assert sample_name_ds is not None
        assert sample_name_ds["config"]["values"] == "SampleA"

        sample_desc_ds = get_by_named_path(doc, path_map, "/entry/sample/description")
        assert sample_desc_ds is not None
        assert sample_desc_ds["config"]["values"] == "A test sample"

        # --- /entry ---
        # check that users metadata is inserted correctly
        john_doe_group = get_by_named_path(doc, path_map, "/entry/user_JohnDoe")
        john_doe_name_ds = get_by_named_path(doc, path_map, "/entry/user_JohnDoe/name")
        john_doe_affil_ds = get_by_named_path(
            doc, path_map, "/entry/user_JohnDoe/affiliation"
        )
        john_doe_id_ds = get_by_named_path(
            doc, path_map, "/entry/user_JohnDoe/facility_user_id"
        )
        assert john_doe_name_ds is not None
        assert john_doe_name_ds["config"]["values"] == "John Doe"
        assert john_doe_affil_ds is not None
        assert (
            john_doe_affil_ds["config"]["values"]
            == "European Spallation Source ERIC (ESS)"
        )
        assert john_doe_id_ds is not None
        assert john_doe_id_ds["config"]["values"] == "johndoe"
        assert john_doe_group is not None
        assert john_doe_name_ds in john_doe_group["children"]
        assert john_doe_affil_ds in john_doe_group["children"]
        assert john_doe_id_ds in john_doe_group["children"]

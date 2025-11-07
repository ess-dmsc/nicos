import json
from pathlib import Path

import pytest

from nicos.core import MAIN, POLLER

from nicos_ess.devices.datasinks.nexus_structure import NexusStructureJsonFile

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
        ("Exp", "users"): [[]],
        # No ("Sample", "samples") -> _insert_samples is a no-op
    }


class TestNexusStructureJsonFile(TestCase):
    def create_patch(self, name):
        patcher = mock.patch(name)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    @pytest.fixture(autouse=True)
    def prepare(self, session, monkeypatch):
        # Change working directory to repo root, so relative paths in the setup work.
        repo_root = Path(__file__).resolve().parents[3]
        monkeypatch.chdir(repo_root)

        self.session = session
        self.session.sessiontype = POLLER

        # Start with a clean session, then load a setup that defines "NexusStructure".
        # Adjust the setup name to whatever your test rig provides. If your rig
        # already loads it elsewhere, you can omit these two lines.
        self.session.unloadSetup()
        self.session.loadSetup("ess_nexus_structure", {})  # <-- adjust if needed

        # Grab the device under test
        self.device: NexusStructureJsonFile = self.session.getDevice("NexusStructure")
        self.device.alias = "NexusStructure_Basic"  # match the setup definition

        # Assign parameters directly (keeps things simple for a smoke test).
        self.device.area_det_collector_device = ""  # no area-detector placeholder
        yield
        # Teardown
        self.session.unloadSetup()
        self.session.sessiontype = MAIN

    def test_get_structure_smoke(self):
        """Basic smoke test: loads template, injects metadata & mdat, returns JSON string."""
        metainfo = _minimal_metainfo(counter=7)
        raw = self.device.get_structure(metainfo, counter=7)
        assert isinstance(raw, str)

        doc = json.loads(raw)
        assert isinstance(doc, dict)
        assert "children" in doc and isinstance(doc["children"], list) and doc["children"]

        # Entry group should be first-level child in our template
        entry = doc["children"][0]
        assert entry.get("type") == "group"
        assert entry.get("name") == "entry"
        entry_children = entry.get("children", [])
        assert isinstance(entry_children, list)

        # Check metadata datasets were appended under /entry
        def val_of(name: str):
            for c in entry_children:
                if c.get("module") == "dataset" and c.get("config", {}).get("name") == name:
                    return c["config"].get("values")
            return None

        assert val_of("title") == "Test run"
        assert val_of("experiment_identifier") == "P-001"
        assert val_of("experiment_description") == "Beamtime Title"
        assert val_of("scripts") == "import foo\nrun()"
        assert val_of("entry_identifier") == "7"
        assert val_of("entry_identifier_uuid") == "uuid-123"

        # mdat node present
        assert any(c.get("module") == "mdat" for c in entry_children)

        # instrument group still present
        assert any(
            c.get("type") == "group" and c.get("name") == "instrument"
            for c in entry_children
        )

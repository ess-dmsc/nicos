import pytest

from nicos.core import CommunicationError
from nicos_ess.devices.datasinks.file_writer import generateMetainfo

# Set to None because we load the setup after the mocks are in place.
session_setup = None


class TestFilewriter:
    @pytest.fixture(autouse=True)
    def prepare(self, session):
        self.session = session
        self.session.unloadSetup()
        self.session.loadSetup("ess_experiment", {})
        self.session.loadSetup("ess_motors", {})
        yield
        self.motor1.values["position"] = 0
        self.session.unloadSetup()

    def test_metainfo_format(self):
        title = "A test proposal"
        run_title = "A test run"
        users = [
            {
                "name": "John Doe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "johndoe",
            }
        ]
        samples = {0: {"name": "SampleA", "description": "A test sample"}}
        samplename = "SampleA"
        motor_pos = 10
        exp = self.session.getDevice("Exp")
        exp.title = title
        exp.run_title = run_title
        exp.propinfo["users"] = users
        sample = self.session.getDevice("Sample")
        sample.samples = samples
        sample.samplename = samplename
        self.motor1 = self.session.getDevice("motor1")
        self.motor1.values["position"] = motor_pos
        self.session.devices = {"Exp": exp, "Sample": sample, "motor1": self.motor1}
        metainfo = generateMetainfo()
        assert metainfo[("Exp", "title")] == (title, str(title), "", "experiment")
        assert metainfo[("Exp", "run_title")] == (
            run_title,
            str(run_title),
            "",
            "experiment",
        )
        assert metainfo[("Exp", "users")] == (users, str(users[0]), "", "experiment")
        assert metainfo[("Sample", "samples")] == (samples, str(samples), "", "sample")
        assert metainfo[("Sample", "samplename")] == (
            samplename,
            str(samplename),
            "",
            "sample",
        )
        assert metainfo[("motor1", "value")] == (
            motor_pos,
            f"{motor_pos:0.3f}",
            "mm",
            "general",
        )

    def test_metainfo_skips_device_whose_info_fails(self, monkeypatch):
        exp = self.session.getDevice("Exp")
        self.motor1 = self.session.getDevice("motor1")

        def broken_info(dev):
            raise CommunicationError("timed out")

        monkeypatch.setattr(type(self.motor1), "info", broken_info)
        self.session.devices = {"Exp": exp, "motor1": self.motor1}
        metainfo = generateMetainfo()
        assert ("Exp", "title") in metainfo
        assert not any(dev == "motor1" for dev, _ in metainfo)

from unittest.mock import Mock

import pytest

from nicos.core import UsageError
from nicos_ess.devices.experiment import EssExperiment
from nicos_ess.devices.sample import EssSample


@pytest.fixture
def experiment(daemon_device_harness, monkeypatch):
    sample = daemon_device_harness.create_master(
        EssSample,
        name="sample",
    )
    monkeypatch.setattr(
        "nicos_ess.devices.experiment.createThread",
        Mock(),
    )
    experiment = daemon_device_harness.create_master(
        EssExperiment,
        name="experiment",
        cache_filepath="test/nicos_ess/test_devices/data/cached_proposals/cached_proposals_1.json",
        dataroot="test/nicos_ess/test_devices/data",
        sample=sample,
    )
    return experiment


@pytest.fixture()
def session(session):
    session = session
    session.unloadSetup()
    session.loadSetup("ess_experiment", {})
    yield session
    session.unloadSetup()


class TestEssExperiment:
    def test_can_query_yuos(self, experiment):
        assert experiment._canQueryProposals()

    def test_new_experiment_from_cached_proposal(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        # from ExpPanel._set_samples()
        samples = {}
        for index, sample in enumerate(result["samples"]):
            if not sample.get("name", ""):
                sample["name"] = f"sample {index + 1}"
            samples[index] = sample
        experiment.sample.set_samples(dict(samples))

        assert experiment.proposal == "123456"
        assert experiment.title == "A test proposal"
        assert experiment.users == [
            {
                "name": "Jane Doe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "janedoe",
            },
            {
                "name": "John Doe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "johndoe",
            },
        ]
        assert experiment.get_samples() == [
            {
                "name": "cathode coin cell (Charged)",
                "temperature": "0",
                "electric_field": "0",
                "magnetic_field": "0",
            },
            {
                "name": "cathode coin cell (Discharged)",
                "temperature": "0",
                "electric_field": "0",
                "magnetic_field": "0",
            },
        ]

    def test_new_experiment_from_cached_proposal_with_fed_id(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"fed_id": "johndoe"})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)

        assert experiment.proposal == "123456"
        assert experiment.title == "A test proposal"
        assert experiment.users == [
            {
                "name": "Jane Doe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "janedoe",
            },
            {
                "name": "John Doe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "johndoe",
            },
        ]

    def test_no_proposals_using_unknown_fed_id(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"fed_id": "unknownuser"})
        assert len(result) == 0

    def test_update_experiment(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        new_exp_args = {
            "title": "A new proposal title",
            "users": [
                {
                    "name": "JaneJane DoeDoe",
                    "email": "",
                    "affiliation": "European Spallation Source ERIC (ESS)",
                    "facility_user_id": "janejanedoedoe",
                },
            ],
        }
        experiment.update(**new_exp_args)
        assert experiment.proposal == "123456"
        assert experiment.title == "A new proposal title"
        assert experiment.users == [
            {
                "name": "JaneJane DoeDoe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "janejanedoedoe",
            },
        ]

    def test_update_experiment_fails_with_dict_of_users(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        new_exp_args = {
            "title": "A new proposal title",
            "users": {
                "name": "JaneJane DoeDoe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "janejanedoedoe",
            },
        }
        with pytest.raises(UsageError):
            experiment.update(**new_exp_args)

    def test_update_experiment_fails_with_user_missing_name(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        new_exp_args = {
            "title": "A new proposal title",
            "users": [
                {
                    "user": "JaneJane DoeDoe",
                    "email": "",
                    "affiliation": "European Spallation Source ERIC (ESS)",
                    "facility_user_id": "janejanedoedoe",
                },
            ],
        }
        with pytest.raises(KeyError):
            experiment.update(**new_exp_args)

    def test_update_experiment_fails_with_dict_of_local_contacts(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        new_exp_args = {
            "title": "A new proposal title",
            "localcontacts": {
                "name": "JaneJane DoeDoe",
                "email": "",
                "affiliation": "European Spallation Source ERIC (ESS)",
                "facility_user_id": "janejanedoedoe",
            },
        }
        with pytest.raises(UsageError):
            experiment.update(**new_exp_args)

    def test_update_experiment_fails_with_local_contact_missing_name(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        new_exp_args = {
            "title": "A new proposal title",
            "localcontacts": [
                {
                    "contact": "JaneJane DoeDoe",
                    "email": "",
                    "affiliation": "European Spallation Source ERIC (ESS)",
                    "facility_user_id": "janejanedoedoe",
                },
            ],
        }
        with pytest.raises(KeyError):
            experiment.update(**new_exp_args)

    def test_finish_clears_experiment_proposal(self, experiment):
        experiment._yuos_client.update_cache()
        result = experiment._queryProposals(kwds={"admin": True})[0]
        exp_args = {
            "proposal": result["proposal"],
            "title": result["title"],
            "users": result["users"],
        }
        experiment.new(**exp_args)
        # from ExpPanel._set_samples()
        samples = {}
        for index, sample in enumerate(result["samples"]):
            if not sample.get("name", ""):
                sample["name"] = f"sample {index + 1}"
            samples[index] = sample
        experiment.sample.set_samples(dict(samples))
        experiment.finish()
        assert experiment.proposal == "0"
        assert experiment.users == []
        assert experiment.get_samples() == []

    def test_get_current_run_number(self, experiment):
        assert experiment.get_current_run_number() == 1


session_setup = None


class TestEssExperimentWithSession:
    def test_experiment_can_be_created_in_session(self, session):
        assert isinstance(session.experiment, EssExperiment)

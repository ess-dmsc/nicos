from unittest.mock import Mock

from nicos_ess.devices.experiment import EssExperiment
from nicos_ess.devices.sample import EssSample


def test_new_experiment_from_cached_proposal(daemon_device_harness, monkeypatch):
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
        dataroot="",
        sample=sample,
    )

    experiment._yuos_client.update_cache()
    result = experiment._queryProposals(kwds={"admin": True})[0]
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
    # experiment.sample.set_samples(result["samples"])


def test_get_samples(daemon_device_harness, monkeypatch):
    sample = daemon_device_harness.create_master(
        EssSample,
        name="sample",
    )
    experiment = daemon_device_harness.create_master(
        EssExperiment,
        name="experiment",
        cache_filepath="test/nicos_ess/test_devices/data/cached_proposals/cached_proposals_1.json",
        dataroot="",
        sample=sample,
    )
    experiment.sample.set(0, {"name": "sample_a"})
    assert experiment.get_samples() == [{"name": "sample_a"}]

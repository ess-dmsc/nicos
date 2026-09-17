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

    # from ExpPanel._set_samples()
    samples = {}
    for index, sample in enumerate(result["samples"]):
        if not sample.get("name", ""):
            sample["name"] = f"sample {index + 1}"
        samples[index] = sample
    experiment.sample.set_samples(dict(samples))
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

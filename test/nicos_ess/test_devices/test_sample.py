from nicos_ess.devices.sample import EssSample


class TestEssSample:
    def test_sample_get_samples(self, device_harness):
        sample_device = device_harness.create(
            "daemon",
            EssSample,
            name="Sample",
        )
        samples = {0: {"name": "SampleA"}, 1: {"name": "SampleB"}}
        sample_device.set_samples(samples)
        assert sample_device.get_samples() == samples
        assert sample_device.get_samples(as_list=True) == [
            {"name": "SampleA"},
            {"name": "SampleB"},
        ]

    def test_samples_set_samples_from_list(self, device_harness):
        sample_device = device_harness.create(
            "daemon",
            EssSample,
            name="Sample",
        )
        samples = [{"name": "SampleA"}, {"name": "SampleB"}]
        sample_device.set_samples(samples, as_list=True)
        assert sample_device.get_samples() == {
            0: {"name": "SampleA"},
            1: {"name": "SampleB"},
        }

    def test_samples_set_samples_without_name(self, device_harness):
        sample_device = device_harness.create(
            "daemon",
            EssSample,
            name="Sample",
        )
        samples = [{"description": "some_sample"}, {"description": "some_other_sample"}]
        sample_device.set_samples(samples, as_list=True)
        assert sample_device.get_samples() == {
            0: {"description": "some_sample", "name": "sample 1"},
            1: {"description": "some_other_sample", "name": "sample 2"},
        }

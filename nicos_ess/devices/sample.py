from nicos.core import Param
from nicos.core.params import Override
from nicos.devices.sample import Sample


class EssSample(Sample):
    """Device that collects the various sample properties specific to
    samples at ESS.
    """

    parameters = {
        "formula": Param("formula", type=str, settable=True, category="sample"),
        "number_of": Param("number_of", type=int, settable=True, category="sample"),
        "mass_volume": Param("mass/volume", type=str, settable=True, category="sample"),
        "density": Param("density", type=str, settable=True, category="sample"),
        "temperature": Param("temperature", type=str, settable=True, category="sample"),
        "electric_field": Param(
            "electric field", type=str, settable=True, category="sample"
        ),
        "magnetic_field": Param(
            "magnetic field", type=str, settable=True, category="sample"
        ),
    }

    parameter_overrides = {
        "samples": Override(category="sample"),
    }

    def get_samples(self, as_list=False):
        if as_list:
            return [dict(x) for x in self.samples.values()]
        else:
            return self.samples

    def set_samples(self, samples, as_list=False):
        if as_list:
            indexed_samples_dict = {}
            for index, sample in enumerate(samples):
                if not sample.get("name", ""):
                    sample["name"] = f"sample {index + 1}"
                indexed_samples_dict[index] = sample
            samples = indexed_samples_dict
        self.samples = samples

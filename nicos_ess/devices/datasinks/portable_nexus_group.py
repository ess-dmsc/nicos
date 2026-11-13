"""NeXus group of a detector that moves between instruments."""

import numpy as np

from nicos.core import Device, Override, Param, none_or, oneof, tupleof
from nicos_ess.utilities.json_utils import generate_dataset_json, generate_group_json


def ngem_pixel_offsets():
    """Return detector_number and the x, y, z pixel offsets in m.

    Same as generate-detector-geometry portable/ngem/generate.py (36bd364).
    """
    planes, pixels_x, pixels_y = 2, 128, 128
    width, height, coating_spacing, decimals = 0.3, 0.3, 0.01, 4

    pixel_width = width / pixels_x
    pixel_height = height / pixels_y
    column = np.arange(pixels_x)
    row = np.arange(pixels_y)
    plane = np.arange(planes)

    x = np.round(-(width - pixel_width) / 2 + column * pixel_width, decimals)
    y = np.round((height - pixel_height) / 2 - row * pixel_height, decimals)
    z = np.round(np.where(plane == 0, 1.0, -1.0) * coating_spacing / 2, decimals)

    shape = (planes, pixels_y, pixels_x)
    detector_number = (
        pixels_x * pixels_y * plane[:, None, None]
        + pixels_y * row[None, :, None]
        + column[None, None, :]
        + 1
    ).astype(np.int32)
    return (
        detector_number,
        np.broadcast_to(x[None, None, :], shape),
        np.broadcast_to(y[None, :, None], shape),
        np.broadcast_to(z[:, None, None], shape),
    )


GEOMETRIES = {"ngem": ngem_pixel_offsets}

# The detector depends on the first, the last depends on ".".
TRANSLATIONS = (
    ("distance", [0.0, 0.0, 1.0]),
    ("height", [0.0, 1.0, 0.0]),
    ("x_offset", [1.0, 0.0, 0.0]),
)

NEXUS_PATH = "/entry/instrument"


class PortableNexusGroup(Device):
    """Adds the NXdetector group of a portable detector to the NeXus file.

    The device description is written as the detector description.
    """

    parameters = {
        "geometry": Param(
            "Pixel geometry of the detector",
            type=oneof(*GEOMETRIES),
            mandatory=True,
        ),
        "group_name": Param("Name of the NXdetector group", type=str, mandatory=True),
        "source_name": Param("Source name of the event data", type=str, mandatory=True),
        "data_topic": Param("Kafka topic of the event data", type=str, mandatory=True),
        "position": Param(
            "Position as (distance, height, x_offset) in m, along z, y and x",
            type=none_or(tupleof(float, float, float)),
            settable=True,
            userparam=True,
            default=None,
        ),
    }

    parameter_overrides = {
        "visibility": Override(default=("devlist", "namespace")),
    }

    def get_nexus_group(self):
        children = [
            generate_group_json(
                "data",
                "NXevent_data",
                [
                    {
                        "module": "ev44",
                        "config": {
                            "source": self.source_name,
                            "topic": self.data_topic,
                        },
                    }
                ],
            ),
            generate_dataset_json("description", self.description, None),
            *self._position(),
            *self._geometry(),
        ]
        return generate_group_json(self.group_name, "NXdetector", children)

    def _position(self):
        if self.position is None:
            self.log.warning(
                "position not set, writing the detector at the origin: "
                "set %s.position = (distance, height, x_offset)",
                self.name,
            )
            return [generate_dataset_json("depends_on", ".", None)]
        path = f"{NEXUS_PATH}/{self.group_name}/transformations"
        targets = [f"{path}/{name}" for name, _ in TRANSLATIONS[1:]] + ["."]
        translations = []
        for (name, vector), value, depends_on in zip(
            TRANSLATIONS, self.position, targets, strict=True
        ):
            dataset = generate_dataset_json(name, float(value), "m")
            dataset["attributes"] += [
                {
                    "name": "transformation_type",
                    "dtype": "string",
                    "values": "translation",
                },
                {"name": "vector", "dtype": "float", "values": vector},
                {"name": "depends_on", "dtype": "string", "values": depends_on},
            ]
            translations.append(dataset)
        return [
            generate_dataset_json("depends_on", f"{path}/{TRANSLATIONS[0][0]}", None),
            generate_group_json("transformations", "NXtransformations", translations),
        ]

    def _geometry(self):
        detector_number, x, y, z = GEOMETRIES[self.geometry]()
        ids = generate_dataset_json("detector_number", detector_number.tolist(), None)
        ids["config"]["dtype"] = "int32"
        ids["attributes"] = []
        return [
            ids,
            generate_dataset_json("x_pixel_offset", x.tolist(), "m"),
            generate_dataset_json("y_pixel_offset", y.tolist(), "m"),
            generate_dataset_json("z_pixel_offset", z.tolist(), "m"),
        ]

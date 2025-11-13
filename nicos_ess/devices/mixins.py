from nicos.core import DeviceMixinBase, Param
from nicos.core.params import string
from nicos.utils import readonlydict, readonlylist


class nexusconfiglist:
    """a list of NeXus config dicts (items require: group_name, nx_class, dataset_type;
    optionals: units, source_name, suffix, value, schema, topic, protocol, periodic, nexus_path)
    """

    _DATASET_TYPES = ("nx_log", "static_read", "static_value")
    _PROTOCOLS = ("pva", "ca")
    _FORWARDER_REQ = ("schema", "topic", "source_name")  # protocol/periodic optional

    def __call__(self, val=None):
        items = [] if val is None else val
        if not isinstance(items, (list, tuple)):
            raise ValueError("value needs to be a list")

        validated = []
        for idx, raw in enumerate(items):
            if not isinstance(raw, dict):
                raise ValueError(f"nexus_config[{idx}] must be a dict")

            allowed = {
                "group_name",
                "nx_class",
                "units",
                "source_name",
                "suffix",
                "value",
                "schema",
                "topic",
                "protocol",
                "periodic",
                "dataset_type",
                "nexus_path",
            }
            required = {"group_name", "nx_class", "dataset_type"}

            unknown = set(raw) - allowed
            if unknown:
                raise ValueError(
                    f"nexus_config[{idx}] has unknown keys: {sorted(unknown)}"
                )

            missing = required - set(raw)
            if missing:
                raise ValueError(
                    f"nexus_config[{idx}] is missing required keys: {sorted(missing)}"
                )

            out = {}

            # required strings (non-empty)
            group_name = string(raw.get("group_name"))
            if not group_name:
                raise ValueError(
                    f"nexus_config[{idx}].group_name must be a non-empty string"
                )
            out["group_name"] = group_name

            nx_class = string(raw.get("nx_class"))
            if not nx_class:
                raise ValueError(
                    f"nexus_config[{idx}].nx_class must be a non-empty string"
                )
            out["nx_class"] = nx_class

            ds = string(raw.get("dataset_type"))
            if ds not in self._DATASET_TYPES:
                raise ValueError(
                    f"nexus_config[{idx}].dataset_type must be one of {self._DATASET_TYPES}"
                )
            out["dataset_type"] = ds

            if "units" in raw:
                out["units"] = string(raw.get("units", ""))

            if "suffix" in raw:
                out["suffix"] = string(raw.get("suffix", ""))

            if "value" in raw:
                out["value"] = string(raw.get("value", ""))

            if "source_name" in raw:
                # only allowed for nx_log (see cross checks below) but normalize now
                out["source_name"] = string(raw.get("source_name", ""))

            if "schema" in raw:
                out["schema"] = string(raw.get("schema", ""))

            if "topic" in raw:
                out["topic"] = string(raw.get("topic", ""))

            if "protocol" in raw:
                proto = string(raw.get("protocol", ""))
                if proto and proto not in self._PROTOCOLS:
                    raise ValueError(
                        f"nexus_config[{idx}].protocol must be one of {self._PROTOCOLS}"
                    )
                # keep it only if user provided it
                out["protocol"] = proto

            if "periodic" in raw:
                periodic = raw.get("periodic")
                # accept bool or int 0/1, and strings that cast to 0/1
                try:
                    if isinstance(periodic, bool):
                        periodic = int(bool(periodic))
                    else:
                        periodic = int(periodic)
                except Exception:
                    raise ValueError(f"nexus_config[{idx}].periodic must be 0 or 1")
                if periodic not in (0, 1):
                    raise ValueError(f"nexus_config[{idx}].periodic must be 0 or 1")
                out["periodic"] = periodic

            if "nexus_path" in raw:
                npath = string(raw.get("nexus_path"))
                if not npath.startswith("/"):
                    raise ValueError(
                        f"nexus_config[{idx}].nexus_path must be an absolute path"
                    )
                if not npath.startswith("/entry"):
                    raise ValueError(
                        f"nexus_config[{idx}].nexus_path must start with '/entry'"
                    )
                out["nexus_path"] = npath

            # static_value requires presence of 'value' (may be empty string, but must exist)
            if ds == "static_value" and "value" not in raw:
                raise ValueError(
                    f"nexus_config[{idx}] with dataset_type 'static_value' requires the key 'value'"
                )

            # forwarding keys only allowed for nx_log
            fwd_keys_present = {"schema", "topic", "source_name"} & set(raw)
            if ds != "nx_log" and fwd_keys_present:
                raise ValueError(
                    f"nexus_config[{idx}] has forwarding keys {sorted(fwd_keys_present)} "
                    "but dataset_type is not 'nx_log'"
                )

            # nx_log must contain the three: schema/topic/source_name (non-empty)
            if ds == "nx_log":
                missing_fwd = [k for k in self._FORWARDER_REQ if k not in raw]
                if missing_fwd:
                    raise ValueError(
                        f"nexus_config[{idx}] missing required forwarding keys: {sorted(missing_fwd)}"
                    )
                for k in self._FORWARDER_REQ:
                    if not string(raw.get(k, "")):
                        raise ValueError(
                            f"nexus_config[{idx}].{k} must be a non-empty string for 'nx_log'"
                        )

            validated.append(readonlydict(out))

        return readonlylist(validated)


class HasNexusConfig(DeviceMixinBase):
    """
    Mixin class for devices to send data to Kafka and the Nexus file.

    Use `dataset_type` to specify the data handling mode:
    - `"nx_log"`: Forward data to Kafka.
    - `"static_read"`: Add the read value of the device to the Nexus file.
    - `"static_value"`: Add a static string value to the Nexus file.

    Dictionary keys:
        group_name (str): Name of the entry in Nexus.
        nx_class (str): Nexus class.
        units (str, optional): Units of the value.
        source_name (str, optional): PV name or NICOS device name.
        suffix (str, optional): String appended to the group name.
        value (str, optional): Static value to add to Nexus.
        schema (str, optional): Schema used when forwarding data to Kafka.
        topic (str, optional): Kafka topic to forward data to.
        protocol (str, optional): Protocol used when forwarding data to Kafka. One of ["pva" (default), "ca"].
        periodic (int, optional): Whether data is forwarded periodically (0 or 1).
        dataset_type (str): Dataset type, one of ["nx_log" (default), "static_read", "static_value"].
        nexus_path (str, optional): Absolute NeXus path to place the group, e.g. "/entry/instrument" (default) or "/entry/sample".
    """

    parameters = {
        "nexus_config": Param(
            "Nexus structure group definition",
            type=nexusconfiglist(),
            default=[],
            userparam=False,
            settable=True,
        ),
    }

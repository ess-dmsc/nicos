from nicos.core import DeviceMixinBase, Param, anytype, dictof, listof


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
    """

    parameters = {
        "nexus_config": Param(
            "Nexus structure group definition",
            type=listof(dictof(str, anytype)),
            default=[],
            userparam=False,
            settable=True,
        ),
    }

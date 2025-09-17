def generate_nxlog_json(name, schema, source, topic, units):
    return {
        "name": name,
        "type": "group",
        "attributes": [{"name": "NX_class", "dtype": "string", "values": "NXlog"}],
        "children": [
            {
                "module": schema,
                "config": {
                    "source": source,
                    "topic": topic,
                    "dtype": "double",
                    "value_units": units,
                },
            }
        ],
    }


def _parse_dtype(value):
    type_map = {str: "string", bool: "int", int: "int", float: "double"}
    if isinstance(value, list):
        return _parse_dtype(value[0]) if value else "string"
    return type_map.get(type(value), "string")


def generate_dataset_json(name, value, unit):
    attributes = [{"name": "units", "dtype": "string", "values": unit if unit else ""}]
    return {
        "module": "dataset",
        "config": {
            "name": name,
            "values": value,
            "dtype": _parse_dtype(value),
        },
        "attributes": attributes,
    }


def generate_group_json(name, nx_class, children):
    return {
        "name": name,
        "type": "group",
        "attributes": [{"name": "NX_class", "dtype": "string", "values": nx_class}],
        "children": children,
    }


def build_json(groups):
    return [
        generate_group_json(name, group["nx_class"], group["children"])
        for name, group in groups.items()
    ]

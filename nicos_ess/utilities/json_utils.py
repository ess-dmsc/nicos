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

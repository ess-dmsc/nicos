# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Matt Clarke <matt.clarke@ess.eu>
#   Kenan Muric <kenan.muric@ess.eu>
#
# *****************************************************************************
import copy
import json

from nicos import session
from nicos.core import (
    Device,
    NicosError,
    Override,
    Param,
    relative_path,
    ConfigurationError,
)

from nicos_ess.nexus.converter import NexusTemplateConverter


class NexusStructureProvider(Device):
    parameter_overrides = {
        "visibility": Override(default=()),
    }

    def get_structure(self, metainfo, counter):
        raise NotImplementedError("must implement get_structure method")


class NexusStructureJsonFile(NexusStructureProvider):
    parameters = {
        "nexus_config_path": Param(
            "NeXus configuration filepath",
            type=relative_path,
            mandatory=True,
            userparam=True,
            settable=True,
        ),
    }

    def get_structure(self, metainfo, counter):
        structure = self._load_structure()
        structure = self._insert_extra_devices(structure)
        structure = self._filter_structure(structure)
        structure = self._insert_metadata(structure, metainfo, counter)
        return json.dumps(structure)

    def _load_structure(self):
        with open(self.nexus_config_path, "r", encoding="utf-8") as file:
            structure = file.read()
        return json.loads(structure)

    def _check_for_device(self, name):
        try:
            return session.getDevice(name)
        except ConfigurationError:
            return None

    def _filter_structure(self, structure):
        loaded_devices = [str(dev) for dev in session.devices]
        nexus_alias = session.getDevice("NexusStructure").alias

        self._filter_items(structure, self._are_required_devices_loaded, loaded_devices)
        self._filter_items(structure, self._is_nexus_alias_correct, nexus_alias)
        if device := self._check_for_device("component_tracking_ODIN"):
            self._filter_items(
                structure, self._is_tracking_valid, device.valid_components
            )
        return structure

    def _filter_items(self, data, condition_func, condition_arg):
        data["children"] = [
            item for item in data["children"] if condition_func(item, condition_arg)
        ]

        for item in data["children"]:
            if "children" in item:
                self._filter_items(item, condition_func, condition_arg)

    def _are_required_devices_loaded(self, item, loaded_devices):
        if not isinstance(item, dict) or "required_devices" not in item:
            return True

        return all(dev in loaded_devices for dev in item["required_devices"])

    def _is_nexus_alias_correct(self, item, nexus_alias):
        if not isinstance(item, dict) or not item.get("required_nexus"):
            return True

        return item["required_nexus"] == nexus_alias

    def _is_tracking_valid(self, item, valid_tracking):
        if not isinstance(item, dict) or not item.get("required_tracking"):
            return True
        return item["required_tracking"] in valid_tracking

    def _insert_metadata(self, structure, metainfo, counter):
        datasets = [
            self._create_dataset("title", metainfo[("Exp", "title")][0]),
            self._create_dataset(
                "experiment_identifier", metainfo[("Exp", "proposal")][0]
            ),
            self._create_dataset("entry_identifier", str(counter)),
            self._create_dataset("entry_identifier_uuid", metainfo[("Exp", "job_id")]),
        ]
        structure["children"][0]["children"].extend(datasets)
        structure["children"][0]["children"].append(self._create_mdat())
        structure = self._insert_users(structure, metainfo)
        structure = self._insert_samples(structure, metainfo)
        return structure

    def _insert_extra_devices(self, structure):
        if not self._check_for_device("KafkaForwarder"):
            return structure
        extra_devices = session.getDevice("KafkaForwarder").get_nexus_json()

        if self._check_for_device("component_tracking"):
            extra_devices.extend(
                session.getDevice("KafkaForwarder").get_component_nexus_json()
            )

        for item in structure["children"][0]["children"]:  # Entry children
            if item.get("name", "") == "instrument":
                item["children"].extend(extra_devices)
                return structure

        self.log.warning("Could not find the instrument group in the NeXus")
        return structure

    def _generate_nxclass_template(self, nx_class, prefix, entities, skip_keys=None):
        temp = []
        for entity in entities:
            entity_name = entity.get("name", "").replace(" ", "")
            if not entity_name:
                continue

            result = {
                "type": "group",
                "name": f"{prefix}_{entity_name}",
                "attributes": {"NX_class": nx_class},
                "children": [],
            }
            for n, v in entity.items():
                if skip_keys and n in skip_keys:
                    continue
                result["children"].append(
                    {
                        "module": "dataset",
                        "config": {"name": n, "values": v, "dtype": "string"},
                    }
                )
            temp.append(result)
        return temp

    def _generate_samples_group_list(self, entities, skip_keys=None):
        children = []
        for n, v in entities.items():
            if skip_keys and n in skip_keys:
                continue
            children.append(
                {
                    "module": "dataset",
                    "config": {"name": n, "values": v, "dtype": "string"},
                }
            )
        return children

    def _generate_samples_link_list(self, entities):
        children = []
        for n, p in entities.items():
            children.append(
                {
                    "module": "link",
                    "config": {"name": n, "type": "NXlink", "source": p},
                }
            )
        return children

    def _insert_samples(self, structure, metainfo):
        samples_info = metainfo.get(("Sample", "samples"))
        link_info = {
            "temperature": metainfo.get(("Sample", "temperature")),
            "electric_field": metainfo.get(("Sample", "electric_field")),
            "magnetic_field": metainfo.get(("Sample", "magnetic_field")),
        }
        if not samples_info:
            return structure

        samples_dict = samples_info[0][0]
        samples_list = self._generate_samples_group_list(
            samples_dict, skip_keys=["number_of"]
        )

        nxinstrument_structure = self._find_nxinstrument(structure)

        for field_name, field_metainfo in link_info.items():
            value = field_metainfo[0]
            dev_path = self._find_device_path(nxinstrument_structure, value)

            field_dict = (
                {field_name: f"/entry/{'/'.join(dev_path)}"}
                if dev_path
                else {field_name: value}
            )

            if not dev_path:
                session.log.warn(
                    f"Sample field '{field_name}' cannot be linked to device '{value}' since device is not in structure."
                )

            samples_list.extend(self._generate_samples_link_list(field_dict))

        if not samples_list:
            return structure

        for child in structure["children"][0]["children"]:
            if not isinstance(child, dict) or "attributes" not in child:
                continue

            if any(
                attr.get("name") == "NX_class" and attr.get("values") == "NXsample"
                for attr in child["attributes"]
            ):
                child.setdefault("children", []).extend(samples_list)
                return structure

        self.log.warning(
            "Could not find the NXsample group in the NeXus JSON structure"
        )
        return structure

    def _find_nxinstrument(self, structure):
        for child in structure["children"][0]["children"]:
            if not isinstance(child, dict) or "attributes" not in child:
                continue

            if any(
                attr.get("name") == "NX_class" and attr.get("values") == "NXinstrument"
                for attr in child["attributes"]
            ):
                return child

        return None

    def _find_device_path(self, structure, dev_name):
        def search_node(node, path):
            if isinstance(node, dict):
                if node.get("name") == dev_name:
                    return path + [node["name"]]
                if "children" in node:
                    for i, child in enumerate(node["children"]):
                        found_path = search_node(child, path + [node["name"]])
                        if found_path:
                            return found_path
            return None

        return search_node(structure, [])

    def _insert_users(self, structure, metainfo):
        users = self._generate_nxclass_template(
            "NXuser",
            "user",
            metainfo[("Exp", "users")][0],
        )
        if users:
            structure["children"][0]["children"].extend(users)
        return structure

    def _create_dataset(self, name, values):
        return {
            "module": "dataset",
            "config": {"name": name, "values": values, "type": "string"},
        }

    def _create_mdat(self):
        return {
            "module": "mdat",
            "config": {"items": ["start_time", "end_time"]},
        }


class NexusStructureAreaDetector(NexusStructureJsonFile):
    """
    This class adds some extra consideration to instrument setups with
    area detectors with changing image size (e.g. neutron or light tomography).
    """

    parameters = {
        "area_det_collector_device": Param(
            "Area collector device name",
            type=str,
            mandatory=True,
            userparam=True,
            settable=True,
        ),
    }

    def get_structure(self, metainfo, counter):
        structure = self._load_structure()
        structure = self._insert_extra_devices(structure)
        structure = self._filter_structure(structure)
        structure = self._insert_metadata(structure, metainfo, counter)
        structure = self._add_area_detector_array_size(structure)
        return json.dumps(structure)

    def _add_area_detector_array_size(self, structure):
        self._replace_area_detector_placeholder(structure)
        return structure

    def _replace_area_detector_placeholder(self, data):
        for item in data["children"]:
            if isinstance(item, dict):
                if "config" in item and "array_size" in item["config"]:
                    if item["config"]["array_size"] == "$AREADET$":
                        item["config"]["array_size"] = []
                        for val in self._get_detector_device_array_size(item["config"]):
                            item["config"]["array_size"].append(val)
                if "children" in item:
                    self._replace_area_detector_placeholder(item)

    def _get_detector_device_array_size(self, json_config):
        area_detector_collector = session.getDevice(self.area_det_collector_device)
        return area_detector_collector.get_array_size(
            json_config["topic"], json_config["source"]
        )


class NexusStructureTemplate(NexusStructureProvider):
    parameters = {
        "templatesmodule": Param(
            "Python module containing NeXus nexus_templates", type=str, mandatory=True
        ),
        "templatename": Param(
            "Template name from the nexus_templates module", type=str, mandatory=True
        ),
    }

    _templates = []
    _template = None

    def doInit(self, mode):
        self.log.info(self.templatesmodule)
        self._templates = __import__(self.templatesmodule, fromlist=[self.templatename])
        self.log.info("Finished importing nexus_templates")
        self.set_template(self.templatename)

    def set_template(self, val):
        """
        Sets the template from the given template modules.
        Parses the template using *parserclass* method parse. The parsed
        root, event kafka streams and device placeholders are then set.
        :param val: template name
        """
        if not hasattr(self._templates, val):
            raise NicosError(
                "Template %s not found in module %s" % (val, self.templatesmodule)
            )

        self._template = getattr(self._templates, val)

        if self.templatename != val:
            self._setROParam("templatename", val)

    def get_structure(self, metainfo, counter):
        template = copy.deepcopy(self._template)
        converter = NexusTemplateConverter()
        structure = converter.convert(template, metainfo)
        return json.dumps(structure)

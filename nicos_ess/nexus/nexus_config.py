#  -*- coding: utf-8 -*-
# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2021 by the NICOS contributors (see AUTHORS)
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
#   Kenan Muric <kenan.muric@ess.eu>
#
# *****************************************************************************
import json

from nicos import session

CHILDREN = 'children'
experiment_device = 'Exp'


class NexusTemplate:
    """
    Class that can be used to generate a nexus template from a json
    configuration file and additional information from an experiment device.
    """

    def __init__(self, config_path):
        self._config_path = config_path
        self._nxs_template = {}

    def add_proposal_information(self):
        """
        Appends proposal information to the nexus template extracted from the
        json configuration file.
        The proposal information is added as a group in the entry group and
        contains the proposal information as static datasets.
        The entry group is top level and should be present in all valid
        NeXus files.
        """
        proposal_info = session.experiment.get_proposal_info_as_dict()
        self._nxs_template[CHILDREN][0][CHILDREN][-1][CHILDREN] = []
        for field in proposal_info:
            self._nxs_template[CHILDREN][0][CHILDREN][-1][CHILDREN].append(
                {
                    'module': 'dataset',
                    'config': {
                        'name': field,
                        'dtype': 'string',
                        'values': proposal_info[field]}
                }
            )

    def load_config_file(self):
        with open(self._config_path, 'r') as file:
            self._nxs_template = json.load(file)
            props_info_nexus = {'type': 'group',
                                'name': 'proposal_information',
                                CHILDREN: []}
            self._nxs_template[CHILDREN][0][CHILDREN].append(props_info_nexus)

    def __str__(self):
        return json.dumps(self._nxs_template)

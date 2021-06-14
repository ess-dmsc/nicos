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
from nicos_ess.nexus import DeviceDataset

CHILDREN = 'children'
ENTRY = 'entry'
proposal_info_device = 'ProposalInformation'


class NexusTemplate:
    """
    Class that can be used to generate a nexus template from a json
    configuration file and additional stuff from
    """

    def __init__(self, config_path):
        self._config_path = config_path
        with open(self._config_path, 'r') as file:
            self._nxs_template = file.read()

    def add_proposal_information(self):
        """
        Appends proposal information to the nexus template extracted from the
        json configuration file.
        """
        self._nxs_template[CHILDREN][ENTRY][CHILDREN]['proposal_id'] = \
            DeviceDataset(proposal_info_device, 'proposal_id')
        self._nxs_template[CHILDREN][ENTRY][CHILDREN]['experiment_title'] = \
            DeviceDataset(proposal_info_device, 'experiment_title')
        self._nxs_template[CHILDREN][ENTRY][CHILDREN]['users'] = \
            DeviceDataset(proposal_info_device, 'users')
        self._nxs_template[CHILDREN][ENTRY][CHILDREN]['local_contacts'] = \
            DeviceDataset(proposal_info_device, 'local_contacts')
        self._nxs_template[CHILDREN][ENTRY][CHILDREN]['samples'] = \
            DeviceDataset(proposal_info_device, 'samples')







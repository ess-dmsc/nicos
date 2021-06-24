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
#   AÜC Hardal <umit.hardal@ess.eu>
#
# *****************************************************************************

"""LoKI Sample Environment Devices."""
from nicos.core import Device, Param, listof, tupleof


class ThermoStatedCellHolder(Device):
    """
    The device holds fundamental parameters for the sample environment
    `Thermo Stated Cell Holder`. This holder has two rows. Each row can have
    four cartridges (thus in total of eight cartridges).

    Each cartridge can be loaded with three different kind of cell holder,
    namely, `Narrow Cell` with 10 positions, `Wide Cell` with four positions and
    `Rotating Cell` with three positions.
    """
    parameters = {
        'cell_type_indices': Param('Cell type indices',
                                   type=listof(int),
                                   default=[0] * 8,  # Number of cartridges
                                   settable=False
                                   ),
        'cell_type_names': Param('Cell types',
                                 type=listof(str),
                                 default=['Narrow Cell'] * 8,
                                 settable=False
                                 ),
        'first_positions': Param('Scanned first positions',
                                 type=listof(tupleof(float, float)),
                                 default=[(0.0, 0.0)] * 8,
                                 settable=False
                                 ),
        'positions': Param('Calculated positions',
                           type=listof(listof(tupleof(float, float))),
                           settable=False
                           )
    }

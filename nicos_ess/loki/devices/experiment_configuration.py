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

"""LoKI Experiment Configuration Devices."""
from nicos.core import Device, Param


class InstrumentSettings(Device):
    parameters = {
        'x': Param('Aperture x-position',
                   type=float,
                   default=0.0,
                   settable=True,
                   unit='mm',
                   ),
        'y': Param('Aperture y-position',
                   type=float,
                   default=0.0,
                   settable=True,
                   unit='mm',
                   ),
        'width': Param('Aperture width',
                       type=float,
                       default=0.0,
                       settable=True,
                       unit='mm',
                       ),
        'height': Param('Aperture height',
                        type=float,
                        default=0.0,
                        settable=True,
                        unit='mm',
                        ),
        'offset': Param('Detector offset',
                        type=float,
                        default=0.0,
                        settable=True,
                        unit='mm',
                        ),
    }

    def _set_parameter(self, param, value):
        self._setROParam(f'{param}', value)

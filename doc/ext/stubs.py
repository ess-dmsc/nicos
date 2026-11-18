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
#   Georg Brandl <g.brandl@fz-juelich.de>
#   Alexander Lenz <alexander.lenz@frm2.tum.de>
#
# *****************************************************************************

# generate stub TACO modules as needed to be able to import nicos.devices.taco
# modules and document them

from nicos.utils.stubs import generate_stubs


@pytest.fixture(scope='class')
def dataroot(request, session):
    """Dataroot handling fixture"""

    exp = session.experiment
    dataroot = path.join(config.nicos_root, request.module.exp_dataroot)
    os.makedirs(dataroot)

    counter = path.join(dataroot, exp.counterfile)
    updateFileCounter(counter, 'scan', 42)
    updateFileCounter(counter, 'point', 42)

    exp._setROParam('dataroot', dataroot)
    exp.new(1234, user='testuser')
    exp.sample.new({'samplename': 'mysample'})

    return dataroot

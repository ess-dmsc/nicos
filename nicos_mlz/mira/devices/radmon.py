# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2023 by the NICOS contributors (see AUTHORS)
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
#
# *****************************************************************************

import subprocess
import urllib

from nicos.core import NicosError, Readable, status
from nicos.utils import createSubprocess


class RadMon(Readable):

    def doInit(self, mode):
        h = urllib.request.HTTPBasicAuthHandler()
        h.add_password(realm='Administrator or User',
                       uri='http://miracam.mira.frm2.tum.de/IMAGE.JPG',
                       user='mira', passwd='mira')
        self._op = urllib.request.build_opener(h)

    def doRead(self, maxage=0):
        img = self._op.open('http://miracam.mira.frm2.tum.de/IMAGE.JPG').read()
        with open('/tmp/radmon.jpg', 'wb') as f:
            f.write(img)
        p1 = createSubprocess('/usr/local/bin/ssocr -d 3 -i 1 -t 50 -l maximum '
                              'rotate 1 crop 300 157 57 30 '
                              'make_mono invert keep_pixels_filter 5 '
                              '/tmp/radmon.jpg'.split(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = createSubprocess('/usr/local/bin/ssocr -d 1 -i 1 -t 50 -l maximum '
                              'rotate 1 crop 391 125 20 30 '
                              'make_mono invert keep_pixels_filter 5 '
                              '/tmp/radmon.jpg'.split(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out1, err1 = p1.communicate()
        out2, err2 = p2.communicate()
        out1 = out1.strip()
        out2 = out2.strip()
        self.log.warning('out1=%r, out2=%r', out1, out2)
        if err1:
            raise NicosError(self, 'ERROR in mantissa')
        if err2:
            raise NicosError(self, 'ERROR in exponent')
        return 0.01 * float(out1 + b'e-' + out2) * 1e6  # convert to uSv/h

    def doStatus(self, maxage=0):
        return status.OK, ''

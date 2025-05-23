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
#
# *****************************************************************************

"""Test the HTML monitor device."""

from nicos.services.monitor.html import Monitor

session_setup = "monitor-html"


class HtmlTestMonitor(Monitor):
    def mainLoop(self):
        self._rendered_content = "".join(ct.getHTML() for ct in self._content)


class MockOptions:
    fontsize = 12
    padding = 0
    geometry = "fullscreen"
    timefontsize = None


def test_monitor(session):
    mon = session.getDevice("Monitor")
    mon.start(MockOptions)
    mon.run_main_loop()

    assert "Current status" in mon._rendered_content
    assert '<img src="/some/pic.png"' in mon._rendered_content

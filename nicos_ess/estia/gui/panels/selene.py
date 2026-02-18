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
#   Artur Glavic <artur.glavic@psi.ch>
#
# *****************************************************************************
from nicos.clients.gui.panels import Panel
from nicos.clients.gui.utils import loadUi
from nicos.utils import findResource
from nicos_ess.estia.gui.panels.metrology_scene import MetrologyScene
from nicos_ess.estia.gui.panels.robot_scene import RobotScene
from nicos_ess.gui.panels.panel import PanelBase


class SelenePanel(Panel):
    panelName = "Selene panel"

    def __init__(self, parent, client, options):
        PanelBase.__init__(self, parent, client, options)
        loadUi(self, findResource("nicos_ess/estia/gui/panels/selene.ui"))

        screw_group_1 = [
            # relative location of screws in each mirror group
            # (x, z, active, item-1)
            (50, 234, True, 3),
            (50, 64, True, 4),
            (50, 30, True, 5),
            (445, 234, True, 0),
            (445, 128, True, 1),
            (445, 64, True, 2),
            # second guide, not active
            (50, 500 - 128, False, -2),
            (50, 500 - 64, False, -2),
            (50, 500 - 30, False, -2),
            (445, 500 - 234, False, -2),
            (445, 500 - 128, False, -2),
            (445, 500 - 64, False, -2),
        ]

        screw_group_2 = [
            # relative location of screws in each mirror group
            # (x, z, active, item-1)
            (50, 234, False, -2),
            (50, 128, False, -2),
            (50, 64, False, -2),
            (445, 128, False, -2),
            (445, 64, False, -2),
            (445, 30, False, -2),
            # second guide, active
            (50, 500 - 234, True, 5),
            (50, 500 - 128, True, 4),
            (50, 500 - 64, True, 3),
            (445, 500 - 128, True, 2),
            (445, 500 - 64, True, 1),
            (445, 500 - 30, True, 0),
        ]

        screw_groups = (screw_group_1, screw_group_2)

        channels_1 = [
            # (CHi, pos, diagonal)
            ("ch21", (-45, 80), False),
            ("ch22", (-45, 35), False),
            ("ch23", (-46, -144), True),
            ("ch24", (-46, -202), True),
            ("ch17", (45, 80), False),
            ("ch18", (45, 35), False),
            ("ch19", (46, -144), True),
            ("ch20", (46, -202), True),
        ]

        channels_2 = [
            # (CHi, pos, diagonal)
            ("ch21", (-45, 80), False),
            ("ch22", (-45, 35), False),
            ("ch23", (-46, -144), True),
            ("ch24", (-46, -202), True),
            ("ch17", (45, 80), False),
            ("ch18", (45, 35), False),
            ("ch19", (46, -144), True),
            ("ch20", (46, -202), True),
        ]

        channels = (channels_1, channels_2)

        metrology_options = options["metrology_options"]
        self.lblMetrologyTitle.setText(metrology_options.get("title", ""))
        self._metrology_scene = MetrologyScene(
            self, client, metrology_options, channels
        )
        self.metrologyView.setScene(self._metrology_scene)
        self.metrologyView.scale(0.5, 0.5)

        robot_options = options["robot_options"]
        self.lblRobotTitle.setText(robot_options.get("title", ""))
        self._robot_scene = RobotScene(self, client, robot_options, screw_groups)
        self.robotView.setScene(self._robot_scene)
        self.robotView.scale(0.5, 0.5)

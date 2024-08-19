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

        metrology_options = options["metrology_options"]
        self.lblMetrologyTitle.setText(metrology_options.get("title", ""))
        self._metrology_scene = MetrologyScene(self, client, metrology_options)
        self.metrologyView.setScene(self._metrology_scene)
        self.metrologyView.scale(0.5, 0.5)

        robot_options = options["robot_options"]
        self.lblRobotTitle.setText(robot_options.get("title", ""))
        self._robot_scene = RobotScene(self, client, robot_options)
        self.robotView.setScene(self._robot_scene)
        self.robotView.scale(0.5, 0.5)

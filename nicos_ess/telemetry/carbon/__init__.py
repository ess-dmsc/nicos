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
#
#   Jonas Petersson <jonas.petersson@ess.eu>
#
# *****************************************************************************

"""Carbon/Graphite telemetry backend."""

from nicos_ess.telemetry.carbon.cache_metrics import (
    CACHE_STATUS_KEY_SUFFIX,
    CACHE_METRIC_KEY_FILTERS,
    CACHE_VALUE_KEY_SUFFIX,
    CacheMetricsEmitter,
    SCRIPTS_KEY,
)
from nicos_ess.telemetry.carbon.client import CarbonTcpClient
from nicos_ess.telemetry.carbon.config import CarbonConfig
from nicos_ess.telemetry.carbon.log_metrics import (
    CarbonLogLevelCounterHandler,
    create_carbon_log_handlers,
)

__all__ = [
    "CarbonConfig",
    "CarbonTcpClient",
    "CACHE_METRIC_KEY_FILTERS",
    "CACHE_STATUS_KEY_SUFFIX",
    "CACHE_VALUE_KEY_SUFFIX",
    "CacheMetricsEmitter",
    "CarbonLogLevelCounterHandler",
    "SCRIPTS_KEY",
    "create_carbon_log_handlers",
]

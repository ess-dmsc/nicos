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

"""Carbon/Graphite metrics forwarder for the NICOS collector service."""

from nicos import config
from nicos.core import Override
from nicos.core.device import Device
from nicos.services.collector import ForwarderBase
from nicos_ess.telemetry.config import create_carbon_client, read_carbon_config
from nicos_ess.telemetry.metrics import SCRIPTS_KEY, CacheMetricsEmitter


class CarbonForwarder(ForwarderBase, Device):
    """Forward selected collector cache updates to the telemetry pipeline.

    The collector may hand every cache update to this device. The forwarder is
    responsible for filtering down to the keys it understands, translating those
    updates into metrics through :class:`CacheMetricsEmitter`, and ensuring that
    telemetry failures do not bubble back into collector operation. Startup only
    wires configuration and sender state; all metric decisions stay in the
    emitter so the device remains a thin NICOS wrapper.
    """

    parameter_overrides = {
        "keyfilters": Override(
            default=[rf"^{SCRIPTS_KEY}$", r".+/value$"],
            mandatory=False,
        ),
    }

    def doInit(self, _mode):
        self._emitter = None
        self._initFilters()

    def _startWorker(self):
        cfg = read_carbon_config(config)
        if cfg is None:
            self._emitter = None
            self.log.info("Telemetry disabled, CarbonForwarder inactive")
            return
        client = create_carbon_client(cfg)
        self._emitter = CacheMetricsEmitter(
            client,
            cfg.prefix,
            cfg.instrument,
            flush_interval_s=cfg.flush_interval_s,
        )
        self.log.info("CarbonForwarder sending to %s:%d", cfg.host, cfg.port)

    def _putChange(self, timestamp, _ttl, key, _op, value):
        if self._emitter is None or not self._checkKey(key):
            return
        try:
            self._emitter.process_cache_update(timestamp, key, value)
        except Exception:
            self.log.warning("Could not forward telemetry update for %s", key, exc=1)

    def doShutdown(self):
        emitter = getattr(self, "_emitter", None)
        self._emitter = None
        if emitter is not None:
            emitter.close()

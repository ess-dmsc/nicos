"""Carbon/Graphite metrics forwarder for the NICOS collector service."""

from nicos import config
from nicos.core.device import Device
from nicos.services.collector import ForwarderBase
from nicos_ess.telemetry.config import create_carbon_client, read_carbon_config
from nicos_ess.telemetry.metrics import CacheMetricsEmitter


class CarbonForwarder(ForwarderBase, Device):
    """Forwards NICOS cache updates as metrics to Carbon/Graphite."""

    def _startWorker(self):
        cfg = read_carbon_config(config)
        if cfg is None:
            self.log.info("Telemetry disabled, CarbonForwarder inactive")
            self._emitter = None
            return
        client = create_carbon_client(cfg)
        self._emitter = CacheMetricsEmitter(client, cfg.prefix, cfg.instrument)
        self.log.info("CarbonForwarder sending to %s:%d", cfg.host, cfg.port)

    def _putChange(self, timestamp, ttl, key, op, value):
        if self._emitter is not None:
            self._emitter.process_cache_update(timestamp, key, value)

    def doShutdown(self):
        if getattr(self, "_emitter", None) is not None:
            self._emitter.close()

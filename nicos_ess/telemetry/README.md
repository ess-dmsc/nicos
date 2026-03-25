# Telemetry

`nicos_ess.telemetry` contains ESS-specific telemetry backends for NICOS.

Today there is one backend: Carbon/Graphite in `nicos_ess.telemetry.carbon`.

## Quick Start

Telemetry is disabled unless `telemetry_enabled` is truthy.

Minimal `nicos.conf` settings:

```ini
telemetry_enabled = true
telemetry_carbon_host = carbon.example.org
instrument = bifrost
```

Optional settings with defaults:

- `telemetry_carbon_port = 2003`
- `telemetry_prefix = nicosserver`
- `telemetry_flush_interval_s = 10`
- `telemetry_heartbeat_interval_s = 10`
- `telemetry_reconnect_delay_s = 2`
- `telemetry_queue_max = 10000`
- `telemetry_connect_timeout_s = 1`
- `telemetry_send_timeout_s = 1`

Invalid explicit values fail fast with `ConfigurationError`. The telemetry code
does not silently repair malformed config.

## Runtime Flow

There are two integration points back into NICOS.

### Collector cache updates

1. The collector forwards matching cache keys to
   `nicos_ess.devices.carbon_forwarder.CarbonForwarder`.
2. `CarbonForwarder` reads `CarbonConfig` and builds one
   `CacheMetricsEmitter`.
3. `CacheMetricsEmitter` translates supported keys into Carbon metric lines.
4. `CarbonTcpClient` buffers and sends those lines.

### Log records

1. NICOS calls `nicos_ess.get_log_handlers()`.
2. `CarbonConfig.from_nicos_config()` resolves telemetry settings.
3. `CarbonConfig.create_log_handler()` builds one
   `CarbonLogLevelCounterHandler`.
4. The handler counts log records and sends metric lines through
   `CarbonTcpClient`.

## File Map

- `carbon/config.py`
  Strict config parsing and object construction.
- `carbon/client.py`
  Buffered Carbon TCP sender.
- `carbon/paths.py`
  Metric-name and sanitizing helpers. This is the single place that defines the
  Carbon metric schema.
- `carbon/cache_metrics.py`
  Cache-key ownership and cache-to-metric translation.
- `carbon/log_metrics.py`
  Log-to-metric translation and the NICOS log-handler factory.
- `devices/carbon_forwarder.py`
  Thin NICOS collector wrapper for cache metrics.

## Metrics Emitted Today

All metrics live below:

```text
<telemetry_prefix>.<instrument>
```

Current metric families:

- `<root>.session.busy`
  `exp/scripts` translated to `0` or `1`
- `<root>.device.<device>.status`
  `<device>/status` translated to a small ordinal
- `<root>.cache.value_updates.total.count`
  Total `<device>/value` updates seen in one flush window
- `<root>.device.<device>.cache.value_updates.count`
  Per-device `<device>/value` counts in the same flush window
- `<root>.service.<service>.logs.total.count`
  Total log records in one flush window
- `<root>.service.<service>.logs.level.<level>.count`
  Per-level log counts in one flush window
- `<root>.service.<service>.telemetry.heartbeat`
  Liveness heartbeat

## Where To Extend

If you add another cache-derived metric:

1. Update `carbon/cache_metrics.py`.
2. Keep the cache-key classification and the metric translation in that module.
3. Update `CACHE_METRIC_KEY_FILTERS` in the same module so the forwarder and
   emitter stay in sync.
4. Add tests beside the existing Carbon telemetry tests.

If you add another telemetry backend, add it as a sibling package under
`nicos_ess.telemetry`.

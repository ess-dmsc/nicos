# Telemetry

`nicos_ess.telemetry` contains ESS-specific telemetry implementations for
NICOS.

Today the package contains one metrics backend, Carbon/Graphite. The package is
structured so that each telemetry implementation can carry its own config
parsing, transport code, and data translation logic without mixing those
concerns into unrelated backends.

## What This Package Is For

Telemetry code in ESS NICOS has two jobs:

- translate NICOS state into telemetry data
- deliver that data to an external backend

Those jobs are separate from the rest of NICOS:

- NICOS devices, sessions, and cache updates provide the input
- telemetry code decides what to emit and how to send it

The integration points back into NICOS are intentionally small:

- `nicos_ess.devices.carbon_forwarder.CarbonForwarder` forwards selected
  collector cache updates into the Carbon backend
- `nicos_ess.get_log_handlers()` installs telemetry log handlers for the current
  session

## Current Carbon Backend

The Carbon backend lives in `nicos_ess/telemetry/carbon/`:

- `config.py`
  Parses NICOS config into `CarbonConfig`. The config object is also
  responsible for creating the Carbon client used by the backend.
- `client.py`
  Buffered TCP sender for Carbon plaintext metrics.
- `paths.py`
  Helpers for Graphite-safe metric names.
- `cache_metrics.py`
  Translates selected collector cache updates into Carbon metric lines.
- `log_metrics.py`
  Aggregates NICOS log records into Carbon counter metrics and exposes the
  Carbon log-handler factory used by `nicos_ess.get_log_handlers()`.

## Runtime Flow

### Collector cache updates

1. The collector forwards cache updates to
   `nicos_ess.devices.carbon_forwarder.CarbonForwarder`.
2. The forwarder reads `CarbonConfig` from NICOS config.
3. The forwarder creates a `CarbonTcpClient` from that config.
4. `CacheMetricsEmitter` translates relevant cache updates into Carbon metric
   lines.
5. `CarbonTcpClient` buffers and sends those lines to Carbon.

### NICOS log records

1. `nicos_ess.get_log_handlers()` asks the Carbon backend for log handlers.
2. `log_metrics.create_carbon_log_handlers()` reads `CarbonConfig`.
3. `CarbonLogLevelCounterHandler` aggregates log records into Carbon counter
   metrics.
4. The handler sends metric lines through `CarbonTcpClient`.

## Separation Of Concerns

When adding code here, keep these boundaries clear:

- Backend formatting and transport belong in the backend package.
- NICOS-specific wrapper code belongs at the integration edge, not inside the
  transport code.
- Translation code should work on ordinary Python values wherever possible.

For the current Carbon backend that means:

- metric naming, line formatting, and TCP delivery stay in
  `nicos_ess.telemetry.carbon`
- collector-device wiring stays in `nicos_ess.devices.carbon_forwarder`
- session hook wiring stays in `nicos_ess.get_log_handlers()`

## Adding More Carbon Metrics

If you want to report more data to Carbon:

1. Decide where the input comes from:
   collector cache, log records, device code, or another NICOS subsystem.
2. Add the translation logic under `nicos_ess.telemetry.carbon`.
3. Keep the NICOS hook thin and let the backend module own the metric naming
   and delivery.

If a new metric family grows large enough to deserve its own module, add a new
module under `nicos_ess.telemetry.carbon/` rather than overloading the existing
ones.

## Adding Another Telemetry Implementation

If we later add another backend or another telemetry type, add it as a sibling
package under `nicos_ess.telemetry`.

Examples:

- another metrics backend
- tracing
- structured event export

That implementation should carry its own:

- config parsing
- client/transport code
- translation logic
- NICOS-facing factory functions, if needed

Only move code to the `nicos_ess.telemetry` package root when multiple
implementations genuinely share the same concept and the shared abstraction is
clear from real usage.

"""ESS-specific NICOS package hooks."""


def get_log_handlers(config):
    """Return optional ESS-specific log handlers configured for this session."""
    from nicos_ess.telemetry.carbon import create_carbon_log_handlers

    return create_carbon_log_handlers(config)

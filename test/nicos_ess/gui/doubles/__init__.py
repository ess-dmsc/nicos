"""Reusable doubles for ESS GUI tests."""

from test.nicos_ess.gui.doubles.fake_transport import (
    DeviceSpec,
    EXP_PANEL_PROPOSAL_EVAL,
    FakeClientTransport,
    FakeDaemon,
)

__all__ = [
    "DeviceSpec",
    "EXP_PANEL_PROPOSAL_EVAL",
    "FakeClientTransport",
    "FakeDaemon",
]

"""Reusable doubles for ESS GUI tests."""

from test.nicos_ess.gui.doubles.fake_transport import (
    DeviceSpec,
    FakeClientTransport,
    FakeDaemon,
    SetupSpec,
)

__all__ = ["DeviceSpec", "FakeClientTransport", "FakeDaemon", "SetupSpec"]

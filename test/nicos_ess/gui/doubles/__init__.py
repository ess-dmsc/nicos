"""Reusable doubles for ESS GUI tests."""

from test.nicos_ess.gui.doubles.fake_transport import (
    DeviceSpec,
    FakeClientTransport,
    FakeDaemon,
)

__all__ = ["DeviceSpec", "FakeClientTransport", "FakeDaemon"]

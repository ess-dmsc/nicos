"""Package defaults for ESS GUI tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def allow_unknown_fake_daemon_calls():
    """Opt out for tests that intentionally exercise fake-daemon misses."""
    return None


@pytest.fixture(autouse=True)
def strict_fake_daemon_by_default(request):
    if "allow_unknown_fake_daemon_calls" not in request.fixturenames:
        request.getfixturevalue("strict_fake_daemon")
    yield

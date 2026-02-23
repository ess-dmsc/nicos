"""Fixtures for integration smoke tests."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

pytest.importorskip("confluent_kafka")
pytest.importorskip("p4p")

from integration_test.smoke.run_smoke_stack import smoke_client_session


def _manage_kafka() -> bool:
    raw_value = os.environ.get("NICOS_SMOKE_MANAGE_KAFKA")
    if raw_value is None:
        return True
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@pytest.fixture(scope="module")
def smoke_client():
    """Yield a connected daemon client with full smoke stack running."""
    if os.environ.get("NICOS_RUN_SMOKE_INTEGRATION") != "1":
        pytest.skip(
            "set NICOS_RUN_SMOKE_INTEGRATION=1 to run docker-based smoke integration tests"
        )
    if _manage_kafka() and not _docker_available():
        pytest.skip("docker daemon is not available for integration smoke run")

    with smoke_client_session(clean_runtime=True, keep_kafka=False) as client:
        yield client

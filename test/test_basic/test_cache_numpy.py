"""Cache wire values must not depend on NumPy's display options or threads."""

from concurrent.futures import Future
from threading import Thread

import numpy as np
import pytest

from nicos.protocols.cache import cache_dump, cache_load
from nicos.utils import createThread


@pytest.mark.parametrize("context", ["main", "thread", "nicos-thread"])
@pytest.mark.parametrize("legacy", [False, "1.13"])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(np.float64(1.5), id="float64"),
        pytest.param(np.float64(-2.5), id="negative-float64"),
        pytest.param(np.float64(np.inf), id="infinity"),
        pytest.param(np.float64(np.nan), id="nan"),
        pytest.param([np.float64(1.5), np.float64(-2.5)], id="list"),
        pytest.param((200, np.float64(1.5)), id="tuple"),
        pytest.param({"values": [np.float64(1.5)]}, id="nested-dict"),
        pytest.param({np.float64(1.5): "value"}, id="dict-key"),
        pytest.param(np.float32(1.5), id="float32"),
        pytest.param(np.int64(42), id="int64"),
        pytest.param(np.array([1.5, 2.5]), id="array"),
    ],
)
def test_numpy_cache_roundtrip(value, legacy, context):
    result = Future()

    def roundtrip():
        try:
            # Use NumPy's real context manager so test order cannot hide failures.
            with np.printoptions(legacy=legacy):
                result.set_result(cache_load(cache_dump(value)))
        except Exception as error:
            result.set_exception(error)

    if context == "main":
        roundtrip()
    else:
        thread = (
            createThread("numpy-cache-test", roundtrip, start=False)
            if context == "nicos-thread"
            else Thread(target=roundtrip)
        )
        thread.start()
        thread.join(timeout=5)
        assert not thread.is_alive()

    np.testing.assert_equal(result.result(timeout=5), value)

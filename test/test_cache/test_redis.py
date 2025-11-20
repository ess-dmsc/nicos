import logging
import threading
import time
from typing import Union

import pytest
from mock.mock import MagicMock
import fnmatch

from numpy.core.defchararray import isnumeric

from nicos.services.cache.endpoints.redis_client import RedisClient, RedisError
from nicos.services.cache.database import RedisCacheDatabase
from nicos.services.cache.entry import CacheEntry


class RedisClientStub(RedisClient):
    """
    A stub class for the RedisClient class
    """

    def __init__(self, host="localhost", port=6379, db=0):
        super().__init__(host, port, db, injected_redis=RedisStub())


class RedisStubPipeline:
    def __init__(self, redis_stub):
        self._redis = redis_stub
        self._results = []

    def hset(self, *args, **kwargs):
        self._results.append(self._redis.hset(*args, **kwargs))
        return self

    def hgetall(self, key):
        self._results.append(self._redis.hgetall(key))
        return self

    def execute_command(self, command, *args):
        self._results.append(self._redis.execute_command(command, *args))
        return self

    def execute(self):
        results, self._results = self._results, []
        return results

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.execute()


class RedisStub:
    def __init__(self):
        self._fake_db = {}
        self._scripts = {}
        self._cleaner_sha = None

    def hset(self, name, key=None, value=None, mapping=None, items=None):
        # Emulate Redis HSET behaviour: merge into existing hash instead of replacing it.
        if mapping is not None:
            if name not in self._fake_db or not isinstance(self._fake_db[name], dict):
                self._fake_db[name] = {}
            for k, v in mapping.items():
                self._fake_db[name][k] = v
            return len(mapping)

        if items is not None:
            if name not in self._fake_db or not isinstance(self._fake_db[name], dict):
                self._fake_db[name] = {}
            count = 0
            for k, v in items:
                self._fake_db[name][k] = v
                count += 1
            return count

        if key is not None and value is not None:
            if name not in self._fake_db or not isinstance(self._fake_db[name], dict):
                self._fake_db[name] = {}
            self._fake_db[name][key] = value
            return 1

        return 0

    def hgetall(self, key):
        raw = self._fake_db.get(key, {})
        if not isinstance(raw, dict):
            raise RedisError("Corrupted data")
        # Redis returns strings (decoded), so we stringify here as well.
        return {k: str(v) for k, v in raw.items()}

    def exists(self, *names):
        return sum(1 for name in names if name in self._fake_db)

    def execute_command(self, command, *args):
        if command == "TS.CREATE":
            key = args[0]
            if key not in self._fake_db or not isinstance(self._fake_db[key], dict):
                self._fake_db[key] = {}
            return 1

        elif command == "TS.ADD":
            key = args[0]
            ts = int(args[1])
            value = args[2]

            # Rough numeric check (similar enough for tests)
            if isinstance(value, str):
                try:
                    float(value)
                except ValueError:
                    raise RedisError("TSDB: invalid value")
            elif not isinstance(value, (int, float)):
                raise RedisError("TSDB: invalid value")

            if key not in self._fake_db or not isinstance(self._fake_db[key], dict):
                self._fake_db[key] = {}

            # RedisTimeSeries stores numeric values, but the client gives us strings;
            # we store stringified value so TS.RANGE looks like real Redis.
            self._fake_db[key][ts] = str(value)
            return ts

        elif command == "TS.RANGE":
            key = args[0]
            fromtime = int(args[1])
            totime = int(args[2])
            timeseries = self._fake_db.get(key, {})

            # Check for aggregation syntax: TS.RANGE key from to AGGREGATION avg bucket
            aggregation = None
            bucket_size = None
            if len(args) >= 6 and args[3] == "AGGREGATION":
                aggregation = args[4]
                bucket_size = int(args[5])

            # No aggregation: just filter by time and return sorted list.
            if aggregation is None:
                return [
                    [ts, val]
                    for ts, val in sorted(timeseries.items())
                    if fromtime <= ts <= totime
                ]

            # Only 'avg' is currently needed by tests.
            if aggregation.lower() != "avg":
                raise RedisError(f"Unsupported aggregation: {aggregation}")

            # Bucketed aggregation.
            buckets = {}  # bucket_start -> (sum, count)
            for ts, val in timeseries.items():
                if ts < fromtime or ts > totime:
                    continue
                # Convert stored string back to float for averaging.
                num_val = float(val)
                bucket_idx = (ts - fromtime) // bucket_size
                bucket_start = fromtime + bucket_idx * bucket_size
                cur_sum, cur_count = buckets.get(bucket_start, (0.0, 0))
                buckets[bucket_start] = (cur_sum + num_val, cur_count + 1)

            result = []
            for bucket_start in sorted(buckets.keys()):
                s, c = buckets[bucket_start]
                avg = s / c
                # Match Redis’ stringified numeric representation:
                # ints as '15', floats as '15.5', etc.
                if float(avg).is_integer():
                    avg_str = str(int(avg))
                else:
                    avg_str = str(avg)
                result.append([bucket_start, avg_str])

            return result

        elif command == "DEL":
            # Delete all given keys and return number of keys actually removed.
            deleted = 0
            for key in args:
                if key in self._fake_db:
                    self._fake_db.pop(key, None)
                    deleted += 1
            return deleted

        return 0

    def keys(self, pattern="*"):
        return [key for key in self._fake_db.keys() if fnmatch.fnmatch(key, pattern)]

    def pubsub(self):
        return None

    def scan_iter(self, match="*", count=None):
        for key in self._fake_db.keys():
            if fnmatch.fnmatch(key, match):
                yield key

    def pipeline(self, *args, **kwargs):
        return RedisStubPipeline(self)

    def script_load(self, script: str) -> str:
        sha = f"sha{len(self._scripts) + 1}"
        self._scripts[sha] = script
        if self._cleaner_sha is None:
            self._cleaner_sha = sha
        return sha

    def evalsha(self, sha: str, numkeys: int, *args):
        if sha not in self._scripts:
            raise RedisError("NOSCRIPT No matching script")

        now = float(args[0]) if args else time.time()
        return self.clean_expired(now)

    def clean_expired(self, now: Union[float, None] = None) -> int:
        if now is None:
            now = time.time()

        cleaned = 0
        for key, mapping in self._fake_db.items():

            if key.endswith("_ts") or key.endswith("_snapshot"):
                continue
            if not isinstance(mapping, dict):
                continue

            ttl_str   = mapping.get("ttl")
            time_str  = mapping.get("time")
            expired   = mapping.get("expired", "False")

            if ttl_str and ttl_str != "None" and expired == "False":
                try:
                    ttl = float(ttl_str)
                    t0  = float(time_str)
                except (TypeError, ValueError):
                    continue
                if (t0 + ttl) < now:
                    mapping["expired"] = "True"
                    cleaned += 1

        return cleaned


class TestableRedisCacheDatabase(RedisCacheDatabase):
    """
    A subclass of RedisCacheDatabase that allows us to inject a RedisClientStub
    """

    def __init__(self, *args, **kwargs):
        name = "TestableRedisCacheDatabase"
        self._name = name
        self._config = {}
        self._params = {"name": name}
        self._infoparams = []
        self._adevs = {}
        self._sdevs = set()
        self._controllers = set()
        self._cache = None
        self.log = logging.getLogger(name)
        self.log.setLevel(logging.DEBUG)
        self.doInit("test", injected_client=RedisClientStub())

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)


def _store_ttl_entry(db, category: str, subkey: str,
                     *, ttl: Union[float, None], value="some_value") -> CacheEntry:
    entry = CacheEntry(time.time(), ttl, value)
    db._set_data(category, subkey, entry)
    return entry


def _dummy_iter():
    yield (("dummy", "key"), CacheEntry(time.time(), None, "val"))


@pytest.fixture
def redis_client():
    return RedisClientStub()


@pytest.fixture
def db(redis_client):
    return TestableRedisCacheDatabase(injected_client=redis_client)


@pytest.fixture(autouse=True)
def _isolate_redis_snapshot():
    yield
    RedisCacheDatabase._snapshot_ready = threading.Event()
    RedisCacheDatabase._snapshot_data  = []
    RedisCacheDatabase._snapshot_time  = 0.0
    RedisCacheDatabase._snapshot_building = False


def test_format_key(db):
    assert db._format_key("category", "subkey") == (
        "category/subkey",
        "category/subkey_ts",
    )
    assert db._format_key("nocat", "subkey") == ("subkey", "subkey_ts")


def test_literal_or_str(db):
    assert db._literal_or_str("3.14") == 3.14
    assert db._literal_or_str("42") == 42
    assert db._literal_or_str("-3.14") == -3.14
    assert db._literal_or_str("0") == 0
    assert db._literal_or_str("-42") == -42
    assert db._literal_or_str("3.14e10") == 3.14e10
    assert db._literal_or_str("3.14e-10") == 3.14e-10
    assert db._literal_or_str("3.14E10") == 3.14e10
    assert db._literal_or_str("3.14E-10") == 3.14e-10
    assert db._literal_or_str("[10,]") == "[10,]"
    assert db._literal_or_str("[10, 20]") == "[10, 20]"
    assert db._literal_or_str("{'key': 10}") == "{'key': 10}"
    assert db._literal_or_str("{'key': 'value'}") == "{'key': 'value'}"
    assert db._literal_or_str("not_a_number") == "not_a_number"
    assert db._literal_or_str(None) is None


def test_entry_from_hash_results(db):
    data = {"time": "123", "ttl": "456", "value": "some_value", "expired": "False"}
    assert (
        db._entry_from_hash(data).asDict()
        == CacheEntry(123, 456, "some_value").asDict()
    )


def test_set_string_value(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", "some_value"))


def test_set_float_value(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", 3.14))


def test_set_int_value(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", 42))


def test_set_list_value(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", [1, 2, 3]))


def test_set_dict_value(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", {"a": 1, "b": 2}))


def test_can_iterate_entries(db):
    db._set_data("a_test/key", "value", CacheEntry("123", "456", "some_value"))
    db._set_data("b_test/key2", "value2", CacheEntry("124", "456", "some_value2"))

    expected_keys = ["a_test/key/value", "b_test/key2/value2"]
    expected_time = [123, 124]
    expected_ttl = [456, 456]
    expected_value = ["some_value", "some_value2"]

    for i, ((category, subkey), entry) in enumerate(db.iterEntries()):
        assert f"{category}/{subkey}" == expected_keys[i]
        assert entry.time == expected_time[i]
        assert entry.ttl == expected_ttl[i]
        assert entry.value == expected_value[i]


def test_set_float_generates_hash_and_timeseries(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", 3.14))
    assert db._client.keys() == ["test/key/value", "test/key/value_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "456",
        "value": "3.14",
        "expired": "False",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, 3.14).asDict()]


def test_set_list_generates_hash_and_timeseries(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", [10, 20]))
    assert db._client.keys() == ["test/key/value", "test/key/value_l_0_ts", "test/key/value_l_1_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "456",
        "value": "[10, 20]",
        "expired": "False",
        "ts_encoding": "list",
        "ts_children": "0,1",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, [10, 20]).asDict()]


def test_set_dict_generates_hash_and_timeseries(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", {"a": 1, "b": 2}))
    assert db._client.keys() == ["test/key/value", "test/key/value_d_a_ts", "test/key/value_d_b_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "456",
        "value": "{'a': 1, 'b': 2}",
        "expired": "False",
        "ts_encoding": "dict",
        "ts_children": "a,b",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, {"a": 1, "b": 2}).asDict()]


def test_set_tuple_generates_hash_and_timeseries(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", (10, 20)))
    assert db._client.keys() == ["test/key/value", "test/key/value_l_0_ts", "test/key/value_l_1_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "456",
        "value": "(10, 20)",
        "expired": "False",
        "ts_encoding": "list",
        "ts_children": "0,1",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, [10, 20]).asDict()]


def test_status_tuple_generates_hash_and_timeseries(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", (200, "idle")))
    assert db._client.keys() == ["test/key/value", "test/key/value_l_0_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "456",
        "value": "(200, 'idle')",
        "expired": "False",
        "ts_encoding": "list",
        "ts_children": "0",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, [200]).asDict()] # only numeric part stored in TS and plottable return


def test_mixed_dict_generates_hash_and_timeseries(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", {"a": 1, "b": "idle", "c": 3.5}))
    assert db._client.keys() == ["test/key/value", "test/key/value_d_a_ts", "test/key/value_d_c_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "456",
        "value": "{'a': 1, 'b': 'idle', 'c': 3.5}",
        "expired": "False",
        "ts_encoding": "dict",
        "ts_children": "a,c",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, {"a": 1, "c": 3.5}).asDict()] # only numeric parts stored in TS and plottable return


def test_set_list_still_works_with_interval_aggregation(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", [10, 20]))
    db._set_data("test/key", "value", CacheEntry("124", "456", [20, 40]))
    assert db._client.keys() == ["test/key/value", "test/key/value_l_0_ts", "test/key/value_l_1_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "124",
        "ttl": "456",
        "value": "[20, 40]",
        "expired": "False",
        "ts_encoding": "list",
        "ts_children": "0,1",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 125, interval=10)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(122.0, None, [15.0, 30.0]).asDict()] # average of [10,20] and [20,40] starting at t=122 + 10


def test_set_dict_still_works_with_interval_aggregation(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", {"a": 1, "b": 2}))
    db._set_data("test/key", "value", CacheEntry("124", "456", {"a": 3, "b": 4}))
    assert db._client.keys() == ["test/key/value", "test/key/value_d_a_ts", "test/key/value_d_b_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "124",
        "ttl": "456",
        "value": "{'a': 3, 'b': 4}",
        "expired": "False",
        "ts_encoding": "dict",
        "ts_children": "a,b",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 125, interval=10)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(122.0, None, {"a": 2.0, "b": 3.0}).asDict()] # average of {'a':1,'b':2} and {'a':3,'b':4} starting at t=122 + 10


def test_set_status_tuple_still_works_with_interval_aggregation(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", (200, "idle")))
    db._set_data("test/key", "value", CacheEntry("124", "456", (400, "busy")))
    assert db._client.keys() == ["test/key/value", "test/key/value_l_0_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "124",
        "ttl": "456",
        "value": "(400, 'busy')",
        "expired": "False",
        "ts_encoding": "list",
        "ts_children": "0",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 125, interval=10)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(122.0, None, [300.0]).asDict()] # average of [200] and [400] starting at t=122 + 10


def test_set_mixed_dict_still_works_with_interval_aggregation(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", {"a": 1, "b": "idle", "c": 3.5}))
    db._set_data("test/key", "value", CacheEntry("124", "456", {"a": 3, "b": "busy", "c": 4.5}))
    assert db._client.keys() == ["test/key/value", "test/key/value_d_a_ts", "test/key/value_d_c_ts"]
    assert db._client.hgetall("test/key/value") == {
        "time": "124",
        "ttl": "456",
        "value": "{'a': 3, 'b': 'busy', 'c': 4.5}",
        "expired": "False",
        "ts_encoding": "dict",
        "ts_children": "a,c",
    }
    history_query = db.queryHistory(("test/key", "value"), 122, 125, interval=10)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(122.0, None, {"a": 2.0, "c": 4.0}).asDict()] # average of {'a':1,'c':3.5} and {'a':3,'c':4.5} starting at t=122 + 10


def test_can_get_data(db):
    original_cache_entry = CacheEntry(123, 456, 3.14)
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == 3.14


def test_get_data_returns_non_strings_if_possible(db):
    original_cache_entry = CacheEntry("123", "456", "3.14")
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == 3.14


def test_get_data_handle_non_numeric_values(db):
    original_cache_entry = CacheEntry("123", "456", "not_a_number")
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == "not_a_number"


def test_int_preserved_as_int(db):
    original_cache_entry = CacheEntry("123", "456", 42)
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == 42
    assert isinstance(db._get_data("test/key/value").value, int)


def test_float_preserved_as_float(db):
    original_cache_entry = CacheEntry("123", "456", 3.14)
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == 3.14
    assert isinstance(db._get_data("test/key/value").value, float)


def test_query_history(db):
    db._set_data("test/key", "value", CacheEntry(123, 456, 3.14))
    db._set_data("test/key", "value", CacheEntry(124, 456, 3.15))
    db._set_data("test/key", "value", CacheEntry(125, 456, 3.16))
    history_query = db.queryHistory(("test/key", "value"), 123, 125)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [
        CacheEntry(123.0, None, 3.14).asDict(),
        CacheEntry(124.0, None, 3.15).asDict(),
        CacheEntry(125.0, None, 3.16).asDict(),
    ]
    history_query = db.queryHistory(("test/key", "value"), 123, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [
        CacheEntry(123.0, None, 3.14).asDict(),
        CacheEntry(124.0, None, 3.15).asDict(),
    ]

    history_query = db.queryHistory(("test/key", "value"), 124, 125)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [
        CacheEntry(124.0, None, 3.15).asDict(),
        CacheEntry(125.0, None, 3.16).asDict(),
    ]

    history_query = db.queryHistory(("test/key", "value"), 124, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [
        CacheEntry(124.0, None, 3.15).asDict(),
    ]

    history_query = db.queryHistory(("test/key", "value"), 121, 122)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == []

    history_query = db.queryHistory(("test/key", "value"), 126, 127)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == []


def test_can_handle_redis_exception_set_data(db):
    db._client._redis.hset = MagicMock(
        side_effect=RedisError("Mocked RedisError for hset")
    )
    db._set_data("test/key", "value", CacheEntry("123", "456", 3.14))
    assert "test/key/value" not in db._client.keys()
    assert db._client.hgetall("test/key/value") == {}


def test_can_handle_redis_exception_get_data(db):
    db._client._redis.hgetall = MagicMock(
        side_effect=RedisError("Mocked RedisError for hgetall")
    )
    db._set_data("test/key", "value", CacheEntry("123", "456", 3.14))
    assert db._get_data("test/key/value") is None


def test_set_invalid_type_value(db):
    try:
        db._set_data("test/key", "value", CacheEntry("123", "456", object()))
    except TypeError:
        pass
    assert db._get_data("test/key/value") is None


def test_handle_corrupted_data_in_redis(db):
    db._client._redis._fake_db["test/key/value"] = "corrupted_data"
    assert db._get_data("test/key/value") is None


def test_handle_partial_data_in_redis(db):
    db._client._redis._fake_db["test/key/value"] = {
        "time": "123",
        "value": "partial_data",
    }
    data = db._get_data("test/key/value")
    assert data is None


def test_handle_missing_key_in_redis(db):
    assert db._get_data("nonexistent/key") is None


def test_set_and_get_special_characters_in_key(db):
    db._set_data("test/key!@#$", "value", CacheEntry("123", "456", "special_char_key"))
    assert db._get_data("test/key!@#$/value").value == "special_char_key"


def test_query_history_with_no_data(db):
    history_query = db.queryHistory(("nonexistent/key", "value"), 123, 125)
    assert history_query == []


def test_can_handle_get_without_category(db):
    db._client._redis._fake_db["key"] = {
        "time": "123",
        "ttl": "456",
        "value": "some_value",
    }
    result = db.getEntry(("nocat", "key"))
    assert result.time == 123.0
    assert result.ttl == 456.0
    assert result.value == "some_value"


def test_can_handle_set_without_category(db):
    db._set_data("nocat", "key", CacheEntry("123", "456", "some_value"))
    result = db._get_data("key")
    assert result.time == 123.0
    assert result.ttl == 456.0
    assert result.value == "some_value"


def test_can_handle_triple_hash(db):
    db._set_data("nocat", "###", CacheEntry("123", "456", "some_value"))
    assert db._get_data("###") is None


def test_set_data_with_missing_fields(db):
    try:
        db._set_data("test/key", "value", CacheEntry(None, "456", "missing_time"))
    except TypeError:
        pass
    assert db._get_data("test/key/value") is None


def test_entry_is_not_expired_before_ttl(db):
    _store_ttl_entry(db, "ttlcat/key", "value", ttl=0.2)
    result = db.getEntry(("ttlcat/key", "value"))
    assert result is not None
    assert result.expired is False


def test_entry_turns_expired_after_ttl(db):
    ttl = 0.15
    _store_ttl_entry(db, "ttlcat/key2", "value", ttl=ttl)
    time.sleep(ttl + 0.05)
    result = db.getEntry(("ttlcat/key2", "value"))

    assert result is not None
    assert result.expired is True


def test_iterentries_reports_expired_flag(db):
    ttl = 0.1
    _store_ttl_entry(db, "iter/key", "v", ttl=ttl, value=42)
    _store_ttl_entry(db, "iter/key", "v2", ttl=None, value=99)

    time.sleep(ttl + 0.05)

    entries = {(cat + "/" + sub): entry for (cat, sub), entry in db.iterEntries()}

    assert "iter/key/v"  in entries
    assert "iter/key/v2" in entries

    assert entries["iter/key/v" ].expired is True
    assert entries["iter/key/v2"].expired is False


def test_entry_without_ttl_never_expires(db):
    _store_ttl_entry(db, "notimeout/key", "value", ttl=None)
    time.sleep(0.2)
    result = db.getEntry(("notimeout/key", "value"))
    assert result is not None
    assert result.expired is False


def test_explicitly_stored_expired_flag_is_preserved(db):
    entry = CacheEntry(time.time(), 60.0, "foo")
    entry.expired = True
    db._set_data("explicit/key", "val", entry)

    retrieved = db.getEntry(("explicit/key", "val"))
    assert retrieved is not None
    assert retrieved.expired is True


def test_setting_none_or_empty_string_removes_entry(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", "some_value"))
    assert db._get_data("test/key/value") is not None

    db._set_data("test/key", "value", CacheEntry("123", "456", None))
    assert db._get_data("test/key/value") is None

    db._set_data("test/key", "value", CacheEntry("123", "456", ""))
    assert db._get_data("test/key/value") is None

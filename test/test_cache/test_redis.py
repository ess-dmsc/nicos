import logging
import threading
import time
from typing import Union

import pytest
from mock.mock import MagicMock
import fnmatch

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
        if mapping:
            self._fake_db[name] = {k: v for k, v in mapping.items()}
            return len(mapping)
        elif items:
            self._fake_db[name] = {k: v for k, v in items}
            return len(items)
        elif key and value:
            if name not in self._fake_db:
                self._fake_db[name] = {}
            self._fake_db[name][key] = value
            return 1
        return 0

    def hgetall(self, key):
        raw = self._fake_db.get(key, {})
        if not isinstance(raw, dict):
            raise RedisError("Corrupted data")
        return {k: str(v) for k, v in raw.items()}

    def exists(self, *names):
        return sum(1 for name in names if name in self._fake_db)

    def execute_command(self, command, *args):
        if command == "TS.CREATE":
            self._fake_db[args[0]] = {}
        elif command == "TS.ADD":
            self._fake_db[args[0]].update({int(args[1]): str(args[2])})
        elif command == "TS.RANGE":
            fromtime, totime = int(args[1]), int(args[2])
            timeseries = self._fake_db.get(args[0], {})
            return [
                [k, v]
                for k, v in timeseries.items()
                if float(fromtime) <= float(k) <= float(totime)
            ]
        elif command == "DEL":
            for key in args:
                self._fake_db.pop(key, None)
                return len(args)
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

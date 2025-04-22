import logging

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


class RedisStub:
    def __init__(self):
        self._fake_db = {}

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

    def keys(self, pattern="*"):
        return [key for key in self._fake_db.keys() if fnmatch.fnmatch(key, pattern)]

    def pubsub(self):
        return None


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


@pytest.fixture
def redis_client():
    return RedisClientStub()


@pytest.fixture
def db(redis_client):
    return TestableRedisCacheDatabase(injected_client=redis_client)


def test_format_key(db):
    assert db._format_key("category", "subkey") == (
        "category/subkey",
        "category/subkey_ts",
    )
    assert db._format_key("nocat", "subkey") == ("subkey", "subkey_ts")


def test_convert_number_if_possible(db):
    assert db._convert_to_number_if_possible("3.14") == 3.14
    assert db._convert_to_number_if_possible("42") == 42
    assert db._convert_to_number_if_possible("-3.14") == -3.14
    assert db._convert_to_number_if_possible("0") == 0
    assert db._convert_to_number_if_possible("-42") == -42
    assert db._convert_to_number_if_possible("3.14e10") == 3.14e10
    assert db._convert_to_number_if_possible("3.14e-10") == 3.14e-10
    assert db._convert_to_number_if_possible("3.14E10") == 3.14e10
    assert db._convert_to_number_if_possible("3.14E-10") == 3.14e-10
    assert db._convert_to_number_if_possible("[10,]") == "[10,]"
    assert db._convert_to_number_if_possible("[10, 20]") == "[10, 20]"
    assert db._convert_to_number_if_possible("{'key': 10}") == "{'key': 10}"
    assert db._convert_to_number_if_possible("{'key': 'value'}") == "{'key': 'value'}"
    assert db._convert_to_number_if_possible("not_a_number") == "not_a_number"
    assert db._convert_to_number_if_possible(None) is None


def test_format_get_results(db):
    data = {"time": "123", "ttl": "456", "value": "some_value", "expired": "False"}
    assert (
        db._format_get_results(data).asDict()
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
    # create an exception when calling hset. Use mock library
    db._client._redis.hset = MagicMock(
        side_effect=RedisError("Mocked RedisError for hset")
    )
    db._set_data("test/key", "value", CacheEntry("123", "456", 3.14))
    assert "test/key/value" not in db._client.keys()
    assert db._client.hgetall("test/key/value") == {}


def test_can_handle_redis_exception_get_data(db):
    # create an exception when calling hgetall. Use mock library
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

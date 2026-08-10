import fnmatch
import logging
import time
from typing import Union

import pytest
from unittest.mock import MagicMock

from nicos.protocols.cache import cache_dump, cache_load
from nicos.services.cache.database import RedisCacheDatabase
from nicos.services.cache.endpoints.redis_client import RedisClient, RedisError
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
        self._commands = []

    def hset(self, *args, **kwargs):
        self._commands.append((self._redis.hset, args, kwargs))
        return self

    def hgetall(self, key):
        self._commands.append((self._redis.hgetall, (key,), {}))
        return self

    def execute_command(self, command, *args):
        self._commands.append((self._redis.execute_command, (command, *args), {}))
        return self

    def zadd(self, *args, **kwargs):
        self._commands.append((self._redis.zadd, args, kwargs))
        return self

    def execute(self):
        commands, self._commands = self._commands, []
        results = []
        for func, args, kwargs in commands:
            results.append(func(*args, **kwargs))
        return results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.execute()


class RedisStub:
    def __init__(self):
        self._fake_db = {}
        self._ts_retention = {}
        self._zsets = set()
        self.hgetall_calls = []

    def hset(self, name, key=None, value=None, mapping=None, items=None):
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

    def hmget(self, name, keys, *args):
        if isinstance(keys, (list, tuple)):
            fields = list(keys) + list(args)
        else:
            fields = [keys] + list(args)

        raw = self._fake_db.get(name, {})
        if not isinstance(raw, dict):
            raise RedisError("Corrupted data")

        return [str(raw.get(f)) if f in raw else None for f in fields]

    def hgetall(self, key):
        self.hgetall_calls.append(key)
        raw = self._fake_db.get(key, {})
        if not isinstance(raw, dict):
            raise RedisError("Corrupted data")
        # Redis returns strings (decoded), so we stringify here as well.
        return {k: str(v) for k, v in raw.items()}

    def exists(self, *names):
        return sum(1 for name in names if name in self._fake_db)

    @staticmethod
    def _timestamp(value, *, minimum=False):
        if value == "-":
            return float("-inf")
        if value == "+":
            return float("inf")
        return int(value)

    def _store_timeseries_sample(self, key, ts, value):
        if isinstance(value, str):
            try:
                float(value)
            except ValueError:
                raise RedisError("TSDB: invalid value") from None
        elif not isinstance(value, (int, float)):
            raise RedisError("TSDB: invalid value")

        if key not in self._fake_db or not isinstance(self._fake_db[key], dict):
            raise RedisError("TSDB: the key does not exist")

        self._fake_db[key][ts] = str(value)
        retention_ms = self._ts_retention.get(key)
        if retention_ms is not None:
            cutoff = ts - retention_ms
            for old_ts in [k for k in list(self._fake_db[key]) if int(k) <= cutoff]:
                self._fake_db[key].pop(old_ts, None)
        return ts

    def _timeseries_range(self, key, fromtime, totime, options, reverse=False):
        fromtime = self._timestamp(fromtime, minimum=True)
        totime = self._timestamp(totime)
        timeseries = self._fake_db.get(key, {})

        aggregation = None
        bucket_size = None
        alignment = 0
        count = None
        i = 0
        while i < len(options):
            option = options[i]
            if option == "ALIGN":
                alignment = int(options[i + 1])
                i += 2
            elif option == "AGGREGATION":
                aggregation = str(options[i + 1]).lower()
                bucket_size = int(options[i + 2])
                i += 3
            elif option == "COUNT":
                count = int(options[i + 1])
                i += 2
            else:
                i += 1

        samples = [
            (ts, val) for ts, val in timeseries.items() if fromtime <= ts <= totime
        ]
        samples.sort(reverse=reverse)

        if aggregation is not None:
            buckets = {}
            for ts, val in samples:
                bucket = alignment + ((ts - alignment) // bucket_size) * bucket_size
                buckets.setdefault(bucket, []).append(float(val))

            aggregated = []
            for bucket, values in sorted(buckets.items(), reverse=reverse):
                if aggregation == "avg":
                    result = sum(values) / len(values)
                elif aggregation == "max":
                    result = max(values)
                elif aggregation == "last":
                    result = values[-1] if not reverse else values[0]
                else:
                    raise RedisError(f"Unsupported aggregation: {aggregation}")
                result = int(result) if float(result).is_integer() else result
                aggregated.append([bucket, str(result)])
            samples = aggregated
        else:
            samples = [[ts, val] for ts, val in samples]

        return samples[:count] if count is not None else samples

    def execute_command(self, command, *args):
        if command == "TS.CREATE":
            key = args[0]
            retention_ms = None
            i = 1
            while i < len(args):
                if args[i] == "RETENTION" and i + 1 < len(args):
                    retention_ms = int(args[i + 1])
                    i += 2
                    continue
                i += 1
            self._ts_retention[key] = retention_ms
            if key not in self._fake_db or not isinstance(self._fake_db[key], dict):
                self._fake_db[key] = {}
            return 1

        elif command == "TS.ADD":
            key = args[0]
            ts = int(args[1])
            if key not in self._ts_retention:
                if key in self._fake_db:
                    raise RedisError("WRONGTYPE Operation against a key")
                retention_ms = None
                i = 3
                while i < len(args):
                    if args[i] == "RETENTION":
                        retention_ms = int(args[i + 1])
                        i += 2
                    else:
                        i += 1
                self._fake_db[key] = {}
                self._ts_retention[key] = retention_ms
            return self._store_timeseries_sample(key, ts, args[2])

        elif command == "TS.RANGE":
            return self._timeseries_range(args[0], args[1], args[2], args[3:])

        elif command == "TS.REVRANGE":
            return self._timeseries_range(
                args[0], args[1], args[2], args[3:], reverse=True
            )

        elif command == "EXISTS":
            return self.exists(*args)

        elif command == "TS.DEL":
            key = args[0]
            fromtime = float(args[1])
            totime = float(args[2])
            timeseries = self._fake_db.get(key, {})
            if not isinstance(timeseries, dict):
                return 0
            to_remove = [
                ts for ts in list(timeseries.keys()) if fromtime <= ts <= totime
            ]
            for ts in to_remove:
                timeseries.pop(ts, None)
            return len(to_remove)

        elif command == "HDEL":
            key = args[0]
            fields = args[1:]
            mapping = self._fake_db.get(key, {})
            if not isinstance(mapping, dict):
                return 0
            removed = 0
            for f in fields:
                if f in mapping:
                    mapping.pop(f, None)
                    removed += 1
            return removed

        elif command == "ZREMRANGEBYSCORE":
            key = args[0]
            min_score = float(args[1])
            max_score = float(args[2])
            z = self._fake_db.get(key, {})
            if not isinstance(z, dict):
                return 0
            to_remove = [m for m, score in z.items() if min_score <= score <= max_score]
            for m in to_remove:
                z.pop(m, None)
            return len(to_remove)

        elif command == "ZREVRANGEBYSCORE":
            start = num = None
            if len(args) >= 6 and args[3] == "LIMIT":
                start, num = int(args[4]), int(args[5])
            return self.zrevrangebyscore(
                args[0], float(args[1]), float(args[2]), start=start, num=num
            )

        elif command in ("DEL", "UNLINK"):
            # Delete all given keys and return number of keys actually removed.
            deleted = 0
            for key in args:
                if key in self._fake_db:
                    self._fake_db.pop(key, None)
                    self._ts_retention.pop(key, None)
                    self._zsets.discard(key)
                    deleted += 1
            return deleted

        return 0

    def keys(self, pattern="*"):
        return [key for key in self._fake_db if fnmatch.fnmatch(key, pattern)]

    def pubsub(self):
        return None

    def scan_iter(self, match="*", count=None, _type=None):
        for key in self._fake_db:
            if not fnmatch.fnmatch(key, match):
                continue

            if _type == "hash" and (
                key in self._ts_retention
                or key in self._zsets
                or not isinstance(self._fake_db[key], dict)
            ):
                continue
            yield key

    def pipeline(self, *args, **kwargs):
        return RedisStubPipeline(self)

    def zadd(self, name, mapping, *args, **kwargs):
        """
        Very simple ZADD implementation: store as dict member -> score.
        We ignore NX/XX/CH/INCR flags for tests.
        """
        z = self._fake_db.get(name)
        if not isinstance(z, dict):
            z = {}
            self._fake_db[name] = z
        self._zsets.add(name)

        added = 0
        for member, score in mapping.items():
            member_str = str(member)
            if member_str not in z:
                added += 1
            z[member_str] = float(score)

        return added

    def zrangebyscore(
        self,
        name,
        min,
        max,
        start=None,
        num=None,
        withscores=False,
        score_cast_func=float,
    ):
        """
        Minimal ZRANGEBYSCORE for tests.

        Returns members with score in [min, max], ordered by score then member.
        """
        raw = self._fake_db.get(name, {})
        if not isinstance(raw, dict):
            return []

        # Redis allows '-inf', '+inf', numbers, etc. For tests we only need numbers.
        min_score = float(min)
        max_score = float(max)

        items = [
            (member, score)
            for member, score in raw.items()
            if min_score <= score <= max_score
        ]

        # Sort by score, then lexicographically by member
        items.sort(key=lambda ms: (ms[1], ms[0]))

        # Apply offset/limit if provided
        if start is not None or num is not None:
            s = start or 0
            items = items[s : s + num] if num is not None else items[s:]

        if withscores:
            return [(member, score_cast_func(score)) for member, score in items]
        else:
            return [member for member, score in items]

    def zrevrangebyscore(
        self,
        name,
        max,
        min,
        start=None,
        num=None,
        withscores=False,
        score_cast_func=float,
    ):
        result = self.zrangebyscore(
            name,
            min,
            max,
            withscores=withscores,
            score_cast_func=score_cast_func,
        )
        result.reverse()
        if start is not None or num is not None:
            offset = start or 0
            result = (
                result[offset : offset + num] if num is not None else result[offset:]
            )
        return result


class RedisCacheDatabaseHarness(RedisCacheDatabase):
    """
    A subclass of RedisCacheDatabase that allows us to inject a RedisClientStub
    """

    def __init__(self, *args, **kwargs):
        name = "RedisCacheDatabaseHarness"
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
        self.doInit(
            "test", injected_client=kwargs.get("injected_client") or RedisClientStub()
        )

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)


def _store_ttl_entry(
    db, category: str, subkey: str, *, ttl: Union[float, None], value="some_value"
):
    _tell(db, f"{category}/{subkey}", value, time.time(), ttl)


def _dummy_iter():
    yield (("dummy", "key"), CacheEntry(time.time(), None, "val"))


class DummyObject:
    def __init__(self, x):
        self.x = x


class EmptyCacheServer:
    _connected = {}


def _set_historydays(db, days):
    db._params["historydays"] = db.parameters["historydays"].type(days)


def _set_arbitraryhistorydays(db, days):
    db._params["arbitraryhistorydays"] = db.parameters["arbitraryhistorydays"].type(
        days
    )


def _set_maxnativecomponents(db, count):
    db._params["maxnativecomponents"] = db.parameters["maxnativecomponents"].type(count)


@pytest.fixture
def redis_client():
    return RedisClientStub()


@pytest.fixture
def db(redis_client):
    database = RedisCacheDatabaseHarness(injected_client=redis_client)
    database._server = EmptyCacheServer()
    return database


@pytest.fixture
def arbitrary_history(db):
    _set_arbitraryhistorydays(db, 14)


def _tell(db, key, value, timestamp=123.0, ttl=None):
    serialized = None if value is None else cache_dump(value)
    db.tell(key, serialized, timestamp, ttl, None)


def test_redis_keys(db):
    assert db._redis_key("category", "subkey") == "category/subkey"
    assert db._redis_key("nocat", "subkey") == "subkey"
    assert db._arbitrary_key("category/subkey") == "category/subkey_hs"


def test_native_and_arbitrary_retention_are_independent(db):
    _set_historydays(db, 2)
    _set_arbitraryhistorydays(db, 0.5)

    assert db._timeseries_retention_ms() == 2 * 86400 * 1000
    assert db._arbitrary_retention_ms() == 0.5 * 86400 * 1000


def test_retention_conversion_preserves_disabled_and_unlimited_semantics(db):
    assert db._retention_ms(None) is None
    assert db._retention_ms(0) is None
    assert db._retention_ms(1e-12) == 1


def test_entry_from_hash_results(db):
    data = {"time": "123", "ttl": "", "value": "some_value"}
    assert (
        db._entry_from_hash(data).asDict()
        == CacheEntry(123, None, "some_value").asDict()
    )


def test_set_data_only_persists_to_redis(db):
    db._set_data("test/key", "value", CacheEntry(123, None, cache_dump(3.14)))

    assert list(db.iterEntries()) == []
    assert db._client.hgetall("test/key/value") == {
        "time": "123",
        "ttl": "",
        "value": "3.14",
    }


def test_can_iterate_entries(db):
    _tell(db, "a_test/key/value", "some_value", 123, 456)
    _tell(db, "b_test/key2/value2", "some_value2", 124, 456)

    entries = [
        (f"{category}/{subkey}", entry.time, entry.ttl, cache_load(entry.value))
        for (category, subkey), entry in db.iterEntries()
    ]
    assert entries == [
        ("a_test/key/value", 123, 456, "some_value"),
        ("b_test/key2/value2", 124, 456, "some_value2"),
    ]


def test_set_float_generates_hash_and_timeseries(db):
    _tell(db, "test/key/value", 3.14)
    assert db._client.keys() == ["test/key/value", "test/key/value_ts"]
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(123.0, None, 3.14).asDict()]


@pytest.mark.parametrize(
    "value",
    [(10, 20), [10, 20]],
)
def test_numeric_sequence_uses_component_timeseries(db, value):
    _tell(db, "test/device/value", value)

    assert sorted(db._client.keys()) == [
        "test/device/value",
        "test/device/value_ts_0",
        "test/device/value_ts_1",
    ]
    history = db.queryHistory(("test/device", "value"), 122, 124)
    assert [(entry.time, entry.value) for entry in history] == [(123.0, value)]


def test_numeric_dict_uses_component_timeseries(db):
    value = {"low": -100, "high": 150}
    _tell(db, "test/device/limits", value)

    assert sorted(db._client.keys()) == [
        "test/device/limits",
        "test/device/limits_ts_0",
        "test/device/limits_ts_1",
    ]
    history = db.queryHistory(("test/device", "limits"), 122, 124)
    assert [(entry.time, entry.value) for entry in history] == [(123.0, value)]


def test_limit_components_use_last_interval_aggregation(db):
    _tell(db, "test/device/userlimits", (0, 10), 123)
    _tell(db, "test/device/userlimits", (5, 20), 124)

    history = db.queryHistory(("test/device", "userlimits"), 122, 125, interval=10)

    assert [(entry.time, entry.value) for entry in history] == [(122.0, (5, 20))]


def test_oversized_numeric_structure_uses_arbitrary_history(db, arbitrary_history):
    _set_maxnativecomponents(db, 2)
    value = [10, 20, 30]

    _tell(db, "test/device/value", value)

    assert sorted(db._client.keys()) == [
        "test/device/value",
        "test/device/value_hs",
    ]
    history = db.queryHistory(("test/device", "value"), 122, 124)
    assert [cache_load(entry.value) for entry in history] == [value]


def test_status_archives_only_code_natively(db):
    _set_arbitraryhistorydays(db, 14)
    status = (220, "moving")

    _tell(db, "test/device/status", status)

    assert sorted(db._client.keys()) == [
        "test/device/status",
        "test/device/status_ts",
    ]
    assert cache_load(db.getEntry(("test/device", "status")).value) == status
    assert db.queryHistory(("test/device", "status"), 122, 124)[0].value == (
        220,
        None,
    )


def test_status_interval_preserves_most_severe_code(db):
    _tell(db, "test/device/status", (200, "idle"), 123)
    _tell(db, "test/device/status", (240, "error"), 124)
    _tell(db, "test/device/status", (220, "moving"), 125)

    history = db.queryHistory(("test/device", "status"), 122, 126, interval=10)

    assert [(entry.time, entry.value) for entry in history] == [(122.0, (240, None))]


@pytest.mark.parametrize(
    "value",
    [(200, "idle"), {"count": 1, "state": "idle"}],
)
def test_mixed_structure_uses_arbitrary_history(db, arbitrary_history, value):
    _tell(db, "test/key/value", value)

    assert sorted(db._client.keys()) == [
        "test/key/value",
        "test/key/value_hs",
    ]
    history = db.queryHistory(("test/key", "value"), 122, 124)
    assert [cache_load(entry.value) for entry in history] == [value]


def test_set_string_generates_arbitrary_history(db, arbitrary_history):
    _tell(db, "test/key/value", "some_value")
    assert db._client.keys() == [
        "test/key/value",
        "test/key/value_hs",
    ]
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert [cache_load(entry["value"]) for entry in history_query] == ["some_value"]


def test_list_of_strings_generates_arbitrary_history(db, arbitrary_history):
    _tell(db, "test/key/value", ["val1", "val2"])
    assert db._client.keys() == [
        "test/key/value",
        "test/key/value_hs",
    ]
    history_query = db.queryHistory(("test/key", "value"), 122, 124)
    decoded_values = [cache_load(e.value) for e in history_query]
    assert decoded_values == [["val1", "val2"]]


def test_mapped_moveable_arbitrary_history_is_cache_loadable(db, arbitrary_history):
    base = 1763736121.507

    samples = [
        (base + 0.000, "0"),
        (base + 0.700, "In Between"),
        (base + 6.000, "5"),
    ]

    for t, v in samples:
        dumped = cache_dump(v)  # PyON string, e.g. "'0'" or "'In Between'"
        db._set_data("nicos/mapped_values", "value", CacheEntry(str(t), None, dumped))

    history = db.queryHistory(
        ("nicos/mapped_values", "value"),
        samples[0][0] - 1,
        samples[-1][0] + 1,
    )

    assert len(history) == len(samples)
    assert [int(e.time * 1000) for e in history] == [int(t * 1000) for t, _ in samples]

    decoded = [cache_load(e.value) for e in history]
    assert decoded == [v for _, v in samples]


def test_cache_dumped_custom_object_roundtrip_via_arbitrary_history(
    db, arbitrary_history
):
    obj = DummyObject(42)
    dumped = cache_dump(obj)

    # cache_dump(obj) should use cache_unpickle(...) internally
    assert "cache_unpickle(" in dumped

    db._set_data("test/custom", "value", CacheEntry("123", "456", dumped))

    # In Redis we store the PyON string itself
    stored = db._client.hgetall("test/custom/value")
    assert stored["value"] == dumped

    # History delivers the PyON string, which must be cache_load-able
    history = db.queryHistory(("test/custom", "value"), 122, 124)
    assert len(history) == 1

    decoded = cache_load(history[0].value)
    assert isinstance(decoded, DummyObject)
    assert decoded.x == 42


def test_cache_dump_custom_object_history_without_interval(db, arbitrary_history):
    obj1 = DummyObject(1)
    obj2 = DummyObject(2)

    dumped1 = cache_dump(obj1)
    dumped2 = cache_dump(obj2)

    db._set_data("test/custom", "value", CacheEntry("123", "456", dumped1))
    db._set_data("test/custom", "value", CacheEntry("124", "456", dumped2))

    history = db.queryHistory(("test/custom", "value"), 122, 125)
    assert len(history) == 2

    decoded1 = cache_load(history[0].value)
    decoded2 = cache_load(history[1].value)

    assert isinstance(decoded1, DummyObject)
    assert decoded1.x == 1
    assert isinstance(decoded2, DummyObject)
    assert decoded2.x == 2


def test_cache_dump_custom_object_history_with_interval(db, arbitrary_history):
    obj1 = DummyObject(1)
    obj2 = DummyObject(2)

    dumped1 = cache_dump(obj1)
    dumped2 = cache_dump(obj2)

    db._set_data("test/custom", "value", CacheEntry("123", "456", dumped1))
    db._set_data("test/custom", "value", CacheEntry("124", "456", dumped2))

    history = db.queryHistory(("test/custom", "value"), 122, 125, interval=10)
    assert len(history) == 1  # decimated to first

    decoded = cache_load(history[0].value)

    assert isinstance(decoded, DummyObject)
    assert decoded.x == 1


def test_cache_dump_none_is_not_treated_as_delete(db):
    dumped = cache_dump(None)  # "None"

    db._set_data("test/none", "value", CacheEntry("123", "456", dumped))

    # We expect a real entry, not a deletion
    entry = db._get_data("test/none/value")
    assert entry is not None
    assert entry.value == "None"
    assert entry.time == 123.0
    assert entry.ttl == 456.0


def test_cache_dump_list_of_strings_is_cache_loadable_via_arbitrary_history(
    db, arbitrary_history
):
    original = ["val1", "val2"]
    dumped = cache_dump(original)  # "['val1', 'val2']" (PyON)

    db._set_data("test/pyon_list", "value", CacheEntry("123", "456", dumped))

    # Stored verbatim in arbitrary history.
    assert sorted(db._client.keys()) == [
        "test/pyon_list/value",
        "test/pyon_list/value_hs",
    ]
    assert db._client.hgetall("test/pyon_list/value")["value"] == dumped

    history = db.queryHistory(("test/pyon_list", "value"), 122, 124)
    assert len(history) == 1

    decoded = cache_load(history[0].value)
    assert decoded == original


def test_cache_dump_status_tuple_roundtrip_via_arbitrary_history(db, arbitrary_history):
    status = (200, "idle")
    dumped = cache_dump(status)  # "(200, 'idle')"

    db._set_data("test/status_pyon", "value", CacheEntry("123", "456", dumped))

    # Stored verbatim in arbitrary history.
    stored = db._client.hgetall("test/status_pyon/value")
    assert stored["value"] == dumped

    history = db.queryHistory(("test/status_pyon", "value"), 122, 124)
    assert len(history) == 1

    decoded = cache_load(history[0].value)
    assert decoded == status


def test_can_get_data(db):
    original_cache_entry = CacheEntry(123, 456, cache_dump(3.14))
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == "3.14"


def test_get_data_handle_non_numeric_values(db):
    original_cache_entry = CacheEntry("123", "456", cache_dump("not_a_number"))
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert cache_load(db._get_data("test/key/value").value) == "not_a_number"


def test_int_saved_as_string_int(db):
    original_cache_entry = CacheEntry("123", "456", cache_dump(42))
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == "42"
    assert isinstance(db._get_data("test/key/value").value, str)


def test_float_saved_as_string_float(db):
    original_cache_entry = CacheEntry("123", "456", cache_dump(3.14))
    db._set_data("test/key", "value", original_cache_entry)
    assert db._get_data("test/key/value").time == 123.0
    assert db._get_data("test/key/value").ttl == 456.0
    assert db._get_data("test/key/value").value == "3.14"
    assert isinstance(db._get_data("test/key/value").value, str)


def test_query_history(db):
    _tell(db, "test/key/value", 3.14, 123, 456)
    _tell(db, "test/key/value", 3.15, 124, 456)
    _tell(db, "test/key/value", 3.16, 125, 456)
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
        CacheEntry(123.0, None, 3.14).asDict(),
        CacheEntry(124.0, None, 3.15).asDict(),
        CacheEntry(125.0, None, 3.16).asDict(),
    ]

    history_query = db.queryHistory(("test/key", "value"), 124, 124)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [
        CacheEntry(123.0, None, 3.14).asDict(),
        CacheEntry(124.0, None, 3.15).asDict(),
    ]

    history_query = db.queryHistory(("test/key", "value"), 121, 122)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == []

    history_query = db.queryHistory(("test/key", "value"), 126, 127)
    history_query = [entry.asDict() for entry in history_query]
    assert history_query == [CacheEntry(125.0, None, 3.16).asDict()]


def test_can_handle_redis_exception_set_data(db):
    # A fake failure is required to exercise the Redis network-error path.
    db._client._redis.hset = MagicMock(
        side_effect=RedisError("Mocked RedisError for hset")
    )
    db._set_data("test/key", "value", CacheEntry("123", "456", cache_dump(3.14)))
    assert "test/key/value" not in db._client._redis._fake_db
    assert db._client.hgetall("test/key/value") == {}


def test_can_handle_redis_exception_get_data(db):
    # A fake failure is required to exercise the Redis network-error path.
    db._client._redis.hgetall = MagicMock(
        side_effect=RedisError("Mocked RedisError for hgetall")
    )
    db._set_data("test/key", "value", CacheEntry("123", "456", cache_dump(3.14)))
    assert db._get_data("test/key/value") is None


def test_init_database_prefills_recent_from_redis_hashes(db):
    db._client._redis._fake_db["seed/key/value"] = {
        "time": "123.0",
        "ttl": "",
        "value": "10",
    }
    db._client._redis._fake_db["seed/key/text"] = {
        "time": "124.0",
        "ttl": "15.0",
        "value": cache_dump("abc"),
    }

    db.initDatabase()

    numeric = db.getEntry(("seed/key", "value"))
    assert numeric is not None
    assert numeric.time == 123.0
    assert numeric.ttl is None
    assert numeric.value == "10"
    assert numeric.expired is False

    text = db.getEntry(("seed/key", "text"))
    assert text is not None
    assert text.time == 124.0
    assert text.ttl == 15.0
    assert cache_load(text.value) == "abc"
    assert text.expired is True


def test_init_database_only_fetches_current_value_hashes(db):
    db._client._redis._fake_db["seed/key/value"] = {
        "time": "123.0",
        "ttl": "",
        "value": cache_dump("current"),
    }
    db._client.zadd("seed/key/value_hs", {"123000:'old'": 123000})
    db._client._redis.hgetall_calls.clear()

    db.initDatabase()

    assert db._client._redis.hgetall_calls == ["seed/key/value"]


def test_get_entry_lazy_loads_from_redis_and_caches(db):
    db._client._redis._fake_db["lazy/key/value"] = {
        "time": "123.0",
        "ttl": "",
        "value": cache_dump("from_redis"),
    }

    first = db.getEntry(("lazy/key", "value"))
    assert first is not None
    assert cache_load(first.value) == "from_redis"

    # A fake failure verifies that the second read does not reach external Redis.
    db._client._redis.hgetall = MagicMock(
        side_effect=RedisError("Mocked RedisError after cache warmup")
    )

    second = db.getEntry(("lazy/key", "value"))
    assert second is not None
    assert cache_load(second.value) == "from_redis"


def test_update_entries_no_store_updates_ram_only(db):
    entry = CacheEntry(123.0, None, cache_dump(42))

    changed = db.updateEntries(["nostore/key"], "value", True, entry)
    assert changed is True

    assert db._client.hgetall("nostore/key/value") == {}
    stored = db.getEntry(("nostore/key", "value"))
    assert stored is not None
    assert cache_load(stored.value) == 42
    assert stored.time == 123.0


def test_update_entries_noop_on_same_value_returns_false(db):
    initial = CacheEntry(100.0, None, cache_dump("same"))
    repeat = CacheEntry(200.0, None, cache_dump("same"))

    first = db.updateEntries(["noop/key"], "value", False, initial)
    second = db.updateEntries(["noop/key"], "value", False, repeat)

    assert first is True
    assert second is False


def test_update_entries_archives_same_numeric_value_at_each_timestamp(db):
    first = CacheEntry(100.0, None, cache_dump(3.5))
    second = CacheEntry(101.0, None, cache_dump(3.5))

    assert db.updateEntries(["repeat/key"], "value", False, first) is True
    assert db.updateEntries(["repeat/key"], "value", False, second) is False

    history = db.queryHistory(("repeat/key", "value"), 99, 102)
    assert [(entry.time, entry.value) for entry in history] == [
        (100.0, 3.5),
        (101.0, 3.5),
    ]


def test_update_entries_archives_same_arbitrary_value_when_enabled(db):
    _set_arbitraryhistorydays(db, 1)
    value = cache_dump((200, "all good"))

    assert db.updateEntries(
        ["repeat/status"], "value", False, CacheEntry(100.0, None, value)
    )
    assert not db.updateEntries(
        ["repeat/status"], "value", False, CacheEntry(101.0, None, value)
    )

    history = db.queryHistory(("repeat/status", "value"), 99, 102)
    assert [(entry.time, cache_load(entry.value)) for entry in history] == [
        (100.0, (200, "all good")),
        (101.0, (200, "all good")),
    ]


def test_arbitrary_history_replaces_duplicate_timestamp(db, arbitrary_history):
    _tell(db, "duplicate/key/value", "first", 100.0)
    _tell(db, "duplicate/key/value", "last", 100.0)

    history = db.queryHistory(("duplicate/key", "value"), 99, 101)

    assert [(entry.time, cache_load(entry.value)) for entry in history] == [
        (100.0, "last")
    ]


def test_arbitrary_history_is_disabled_by_default(db):
    value = cache_dump((200, "all good"))

    db.updateEntries(
        ["disabled/status"], "value", False, CacheEntry(100.0, None, value)
    )
    db.updateEntries(
        ["disabled/status"], "value", False, CacheEntry(101.0, None, value)
    )

    assert db._client.keys() == ["disabled/status/value"]
    assert db.queryHistory(("disabled/status", "value"), 99, 102) == []


def test_disabling_arbitrary_history_reclaims_existing_series(db):
    _set_arbitraryhistorydays(db, 1)
    value = cache_dump((200, "all good"))
    db._set_data("cleanup/status", "value", CacheEntry(100.0, None, value))
    assert sorted(db._client.keys()) == [
        "cleanup/status/value",
        "cleanup/status/value_hs",
    ]

    _set_arbitraryhistorydays(db, None)
    db._set_data("cleanup/status", "value", CacheEntry(101.0, None, value))

    assert db._client.keys() == ["cleanup/status/value"]


def test_update_entries_refreshes_ttl_and_time_even_when_value_unchanged(db):
    now = time.time()
    first = CacheEntry(now, 10.0, cache_dump("same"))
    second = CacheEntry(now + 1, 30.0, cache_dump("same"))

    db.updateEntries(["ttlrefresh/key"], "value", False, first)
    changed = db.updateEntries(["ttlrefresh/key"], "value", False, second)

    assert changed is False
    stored_hash = db._client.hgetall("ttlrefresh/key/value")
    assert stored_hash["time"] == str(now + 1)
    assert stored_hash["ttl"] == "30.0"


def test_update_entries_pipeline_none_falls_back_without_exception(db):
    # Pipeline creation is an external Redis failure with a direct-write fallback.
    db._client.pipeline = MagicMock(return_value=None)

    changed = db.updateEntries(
        ["pipeline/key"], "value", False, CacheEntry(123.0, None, cache_dump(3.14))
    )

    assert changed is True
    stored_hash = db._client.hgetall("pipeline/key/value")
    assert stored_hash["value"] == "3.14"
    assert stored_hash["time"] == "123.0"


def test_update_entries_uses_pipeline_for_persisted_updates(db):
    pipe = db._client._redis.pipeline()
    # Redis is the external boundary under test, so record the pipeline flush.
    pipe.execute = MagicMock(wraps=pipe.execute)
    db._client.pipeline = MagicMock(return_value=pipe)

    changed = db.updateEntries(
        ["pipeline/used"], "value", False, CacheEntry(321.0, None, cache_dump(6.28))
    )

    assert changed is True
    pipe.execute.assert_called_once()


def test_switching_from_list_to_scalar_replaces_component_history(db):
    _tell(db, "transition/key/value", [10, 20], 123)
    _tell(db, "transition/key/value", 3.5, 124)

    assert sorted(db._client.keys()) == [
        "transition/key/value",
        "transition/key/value_ts",
    ]
    history = db.queryHistory(("transition/key", "value"), 122, 125)
    assert [(entry.time, entry.value) for entry in history] == [(124.0, 3.5)]


def test_restart_preserves_layout_for_shape_changes(redis_client):
    db = RedisCacheDatabaseHarness(injected_client=redis_client)
    db._server = EmptyCacheServer()
    _tell(db, "transition/key/value", [10, 20], 123)

    restarted = RedisCacheDatabaseHarness(injected_client=redis_client)
    restarted._server = EmptyCacheServer()
    _tell(restarted, "transition/key/value", 3.5, 124)

    assert sorted(restarted._client.keys()) == [
        "transition/key/value",
        "transition/key/value_ts",
    ]


def test_set_invalid_type_value(db):
    db._set_data("test/key", "value", CacheEntry("123", "456", object()))
    assert db._get_data("test/key/value") is None


def test_handle_corrupted_data_in_redis(db):
    db._client._redis._fake_db["test/key/value"] = "corrupted_data"
    assert db._get_data("test/key/value") is None


def test_handle_missing_key_in_redis(db):
    assert db._get_data("nonexistent/key") is None


def test_set_and_get_special_characters_in_key(db):
    value = cache_dump("special_char_key")
    db._set_data("test/key!@#$", "value", CacheEntry("123", "456", value))
    assert db._get_data("test/key!@#$/value").value == value


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
    value = cache_dump("some_value")
    db._set_data("nocat", "key", CacheEntry("123", "456", value))
    result = db._get_data("key")
    assert result.time == 123.0
    assert result.ttl == 456.0
    assert result.value == value


def test_can_handle_triple_hash(db):
    db._set_data("nocat", "###", CacheEntry("123", "456", cache_dump("some_value")))
    assert db._get_data("###") is None


def test_set_data_with_missing_fields(db):
    db._set_data(
        "test/key", "value", CacheEntry(None, "456", cache_dump("missing_time"))
    )
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

    assert "iter/key/v" in entries
    assert "iter/key/v2" in entries

    assert entries["iter/key/v"].expired is True
    assert entries["iter/key/v2"].expired is False


def test_entry_without_ttl_never_expires(db):
    _store_ttl_entry(db, "notimeout/key", "value", ttl=None)
    time.sleep(0.2)
    result = db.getEntry(("notimeout/key", "value"))
    assert result is not None
    assert result.expired is False


def test_scalar_timeseries_rollover_trims_old_samples_but_keeps_current_key(db):
    _set_historydays(db, 1)
    t_old = 100.0
    t_new = t_old + 2 * 86400

    _tell(db, "roll/scalar/value", 1.0, t_old)
    _tell(db, "roll/scalar/value", 2.0, t_new)

    ts_store = db._client._redis._fake_db["roll/scalar/value_ts"]
    assert ts_store == {int(t_new * 1000): "2.0"}

    history = db.queryHistory(("roll/scalar", "value"), t_old - 1, t_new + 1)
    assert [entry.asDict() for entry in history] == [
        CacheEntry(t_new, None, 2.0).asDict()
    ]

    latest = db._get_data("roll/scalar/value")
    assert latest is not None
    assert latest.value == "2.0"
    assert latest.time == t_new


def test_component_timeseries_use_native_retention(db):
    _set_historydays(db, 1)
    old_time = 100.0
    new_time = old_time + 2 * 86400

    _tell(db, "roll/detector/value", [1, 2, 3], old_time)
    _tell(db, "roll/detector/value", [4, 5, 6], new_time)

    for component, expected in enumerate((4, 5, 6)):
        key = f"roll/detector/value_ts_{component}"
        assert db._client._redis._fake_db[key] == {int(new_time * 1000): str(expected)}
    history = db.queryHistory(("roll/detector", "value"), old_time - 1, new_time + 1)
    assert [(entry.time, entry.value) for entry in history] == [(new_time, [4, 5, 6])]


def test_deleting_numeric_structure_removes_all_component_series(db):
    _tell(db, "delete/detector/value", [1, 2, 3], 100)
    _tell(db, "delete/detector/value", None, 101)

    assert db._client.keys() == []


def test_arbitrary_history_rollover_trims_old_samples_but_keeps_current_key(db):
    _set_arbitraryhistorydays(db, 1)
    t_old = 200.0
    t_new = t_old + 2 * 86400
    old_dumped = cache_dump({"state": "old"})
    new_dumped = cache_dump({"state": "new"})

    db._set_data("roll/custom", "value", CacheEntry(t_old, None, old_dumped))
    db._set_data("roll/custom", "value", CacheEntry(t_new, None, new_dumped))

    timestamp = int(t_new * 1000)
    history_set = db._client._redis._fake_db["roll/custom/value_hs"]
    assert history_set == {f"{timestamp}:{new_dumped}": float(timestamp)}

    history = db.queryHistory(("roll/custom", "value"), t_old - 1, t_new + 1)
    assert [cache_load(entry.value) for entry in history] == [{"state": "new"}]

    latest = db.getEntry(("roll/custom", "value"))
    assert latest is not None
    assert cache_load(latest.value) == {"state": "new"}


def test_expired_flag_is_derived_instead_of_persisted(db):
    entry = CacheEntry(time.time(), 60.0, cache_dump("foo"))
    entry.expired = True
    db._set_data("explicit/key", "val", entry)

    assert "expired" not in db._client.hgetall("explicit/key/val")
    retrieved = db.getEntry(("explicit/key", "val"))
    assert retrieved is not None
    assert retrieved.expired is False


def test_setting_none_removes_entry(db):
    db._set_data(
        "test/key", "value", CacheEntry("123", "456", cache_dump("some_value"))
    )
    assert db._get_data("test/key/value") is not None

    db._set_data("test/key", "value", CacheEntry("123", "456", None))
    assert db._get_data("test/key/value") is None

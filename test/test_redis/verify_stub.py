# This file verifies the stub implementation of the RedisClient class.
# If this is included in the automated tests, a Redis server must be deployed.
# For now, we can manually run this file to verify the stub implementation.

import pytest

from nicos.services.cache.endpoints.redis_client import RedisClient
from test.test_cache.test_redis import RedisClientStub


@pytest.fixture(scope="function")
def real_redis_client():
    client = RedisClient(host="localhost", port=6379, db=15)
    client.execute_command("FLUSHDB")
    yield client
    client.execute_command("FLUSHDB")
    client.close()


@pytest.fixture(scope="function")
def stub_redis_client():
    client = RedisClientStub()
    yield client


def test_hset_hgetall(real_redis_client, stub_redis_client):
    key = "test_key"
    mapping = {"field1": "value1", "field2": "value2"}

    real_redis_client.hset(key, mapping=mapping)
    stub_redis_client.hset(key, mapping=mapping)

    real_data = real_redis_client.hgetall(key)
    stub_data = stub_redis_client.hgetall(key)

    assert real_data == stub_data


def test_exists(real_redis_client, stub_redis_client):
    key = "test_exists_key"
    mapping = {"field1": "value1"}

    real_redis_client.hset(key, mapping=mapping)
    stub_redis_client.hset(key, mapping=mapping)

    real_exists = real_redis_client.exists(key)
    stub_exists = stub_redis_client.exists(key)

    assert real_exists == stub_exists


def test_execute_command_ts_create_add_range(real_redis_client, stub_redis_client):
    key = "test_ts_key"
    real_redis_client.execute_command("TS.CREATE", key)
    stub_redis_client.execute_command("TS.CREATE", key)

    real_redis_client.execute_command("TS.ADD", key, 1, 10)
    stub_redis_client.execute_command("TS.ADD", key, 1, 10)

    real_redis_client.execute_command("TS.ADD", key, 2, 20)
    stub_redis_client.execute_command("TS.ADD", key, 2, 20)

    real_range = real_redis_client.execute_command("TS.RANGE", key, 0, 3)
    stub_range = stub_redis_client.execute_command("TS.RANGE", key, 0, 3)

    assert real_range == stub_range

    command = ("TS.REVRANGE", key, 0, 3, "COUNT", 1)
    assert real_redis_client.execute_command(
        *command
    ) == stub_redis_client.execute_command(*command)


def test_keys(real_redis_client, stub_redis_client):
    real_keys = real_redis_client.keys()
    stub_keys = stub_redis_client.keys()

    assert sorted(real_keys) == sorted(stub_keys)


def test_pubsub(real_redis_client, stub_redis_client):
    real_pubsub = real_redis_client.pubsub()
    stub_pubsub = stub_redis_client.pubsub()

    assert real_pubsub is not None
    assert stub_pubsub is None


def test_scan_iter(real_redis_client, stub_redis_client):
    keys = ["test_key1", "test_key2", "test_key3"]
    mapping = {"field1": "value1", "field2": "value2"}

    for key in keys:
        real_redis_client.hset(key, mapping=mapping)
        stub_redis_client.hset(key, mapping=mapping)

    real_keys = list(real_redis_client.scan_iter())
    stub_keys = list(stub_redis_client.scan_iter())

    assert sorted(real_keys) == sorted(stub_keys)


def test_pipeline(real_redis_client, stub_redis_client):
    with real_redis_client._redis.pipeline() as pipe:
        pipe.hset("pipeline_key", "field1", "value1")
        pipe.hgetall("pipeline_key")
        real_results = pipe.execute()

    with stub_redis_client._redis.pipeline() as pipe:
        pipe.hset("pipeline_key", "field1", "value1")
        pipe.hgetall("pipeline_key")
        stub_results = pipe.execute()

    assert real_results == stub_results


def test_hset_mapping_merges_fields(real_redis_client, stub_redis_client):
    key = "hash_merge_key"

    # Initial mapping
    mapping1 = {"field1": "value1", "field2": "value2"}
    real_redis_client.hset(key, mapping=mapping1)
    stub_redis_client.hset(key, mapping=mapping1)

    # Second mapping updates field2 and adds field3
    mapping2 = {"field2": "new_value2", "field3": "value3"}
    real_redis_client.hset(key, mapping=mapping2)
    stub_redis_client.hset(key, mapping=mapping2)

    real_data = real_redis_client.hgetall(key)
    stub_data = stub_redis_client.hgetall(key)

    assert real_data == stub_data
    assert real_data == {
        "field1": "value1",
        "field2": "new_value2",
        "field3": "value3",
    }


def test_execute_command_ts_range_aggregation(real_redis_client, stub_redis_client):
    key = "agg_ts_key"
    real_redis_client.execute_command("TS.CREATE", key)
    stub_redis_client.execute_command("TS.CREATE", key)

    # Timestamps in ms; two buckets of 50ms: [0,49], [50,99]
    points = [
        (10, 10),
        (40, 20),
        (60, 30),
        (90, 50),
    ]

    for ts, val in points:
        real_redis_client.execute_command("TS.ADD", key, ts, val)
        stub_redis_client.execute_command("TS.ADD", key, ts, val)

    # Aggregate over [0, 100] with bucket size 50ms
    real_range = real_redis_client.execute_command(
        "TS.RANGE", key, 0, 100, "AGGREGATION", "avg", 50
    )
    stub_range = stub_redis_client.execute_command(
        "TS.RANGE", key, 0, 100, "AGGREGATION", "avg", 50
    )

    # Ensure timestamps match
    assert [r[0] for r in real_range] == [s[0] for s in stub_range]
    # Ensure values match exactly (string representations too)
    assert real_range == stub_range


def test_execute_command_hdel(real_redis_client, stub_redis_client):
    key = "hdel_key"
    mapping = {"a": "1", "b": "2", "c": "3"}
    real_redis_client.hset(key, mapping=mapping)
    stub_redis_client.hset(key, mapping=mapping)

    real_removed = real_redis_client.execute_command("HDEL", key, "b", "c")
    stub_removed = stub_redis_client.execute_command("HDEL", key, "b", "c")
    assert real_removed == stub_removed
    assert (
        real_redis_client.hgetall(key) == stub_redis_client.hgetall(key) == {"a": "1"}
    )


def test_execute_command_zremrangebyscore(real_redis_client, stub_redis_client):
    key = "zrem_key"
    mapping = {"m1": 1.0, "m2": 2.0, "m3": 3.0}
    real_redis_client.zadd(key, mapping)
    stub_redis_client.zadd(key, mapping)

    real_removed = real_redis_client.execute_command(
        "ZREMRANGEBYSCORE", key, float("-inf"), 2.0
    )
    stub_removed = stub_redis_client.execute_command(
        "ZREMRANGEBYSCORE", key, float("-inf"), 2.0
    )
    assert real_removed == stub_removed

    real_remaining = real_redis_client.zrangebyscore(
        key, float("-inf"), float("inf"), withscores=True
    )
    stub_remaining = stub_redis_client.zrangebyscore(
        key, float("-inf"), float("inf"), withscores=True
    )
    assert real_remaining == stub_remaining == [("m3", 3.0)]


def test_execute_command_ts_del(real_redis_client, stub_redis_client):
    key = "ts_del_key"
    real_redis_client.execute_command("TS.CREATE", key)
    stub_redis_client.execute_command("TS.CREATE", key)

    for ts, val in [(10, 1), (20, 2), (30, 3)]:
        real_redis_client.execute_command("TS.ADD", key, ts, val)
        stub_redis_client.execute_command("TS.ADD", key, ts, val)

    real_deleted = real_redis_client.execute_command("TS.DEL", key, 0, 20)
    stub_deleted = stub_redis_client.execute_command("TS.DEL", key, 0, 20)
    assert real_deleted == stub_deleted

    real_range = real_redis_client.execute_command("TS.RANGE", key, 0, 100)
    stub_range = stub_redis_client.execute_command("TS.RANGE", key, 0, 100)
    assert real_range == stub_range == [[30, "3"]]


def test_execute_command_ts_add_creates_with_retention(
    real_redis_client, stub_redis_client
):
    key = "ts_retention_key"
    for ts, val in [(10, 1), (40, 2), (70, 3)]:
        command = (
            "TS.ADD",
            key,
            ts,
            val,
            "RETENTION",
            50,
            "DUPLICATE_POLICY",
            "LAST",
        )
        real_redis_client.execute_command(*command)
        stub_redis_client.execute_command(*command)

    real_range = real_redis_client.execute_command("TS.RANGE", key, 0, 100)
    stub_range = stub_redis_client.execute_command("TS.RANGE", key, 0, 100)
    assert real_range == stub_range == [[40, "2"], [70, "3"]]


@pytest.mark.parametrize("aggregation", ["avg", "last", "max"])
def test_execute_command_ts_range_aligned_aggregations(
    real_redis_client, stub_redis_client, aggregation
):
    key = f"aligned-{aggregation}"
    real_redis_client.execute_command("TS.CREATE", key)
    stub_redis_client.execute_command("TS.CREATE", key)
    for timestamp, value in ((10, 1), (40, 5), (60, 2), (90, 8)):
        real_redis_client.execute_command("TS.ADD", key, timestamp, value)
        stub_redis_client.execute_command("TS.ADD", key, timestamp, value)

    command = (
        "TS.RANGE",
        key,
        5,
        100,
        "ALIGN",
        5,
        "AGGREGATION",
        aggregation,
        50,
    )
    assert real_redis_client.execute_command(
        *command
    ) == stub_redis_client.execute_command(*command)


def test_execute_command_zrevrangebyscore(real_redis_client, stub_redis_client):
    mapping = {"old": 10, "middle": 20, "new": 30}
    real_redis_client.zadd("reverse-index", mapping)
    stub_redis_client.zadd("reverse-index", mapping)

    command = (
        "ZREVRANGEBYSCORE",
        "reverse-index",
        25,
        float("-inf"),
        "LIMIT",
        0,
        1,
    )
    real_result = real_redis_client.execute_command(*command)
    stub_result = stub_redis_client.execute_command(*command)

    assert real_result == stub_result == ["middle"]

    real_result = real_redis_client.zrevrangebyscore(
        "reverse-index", 25, float("-inf"), start=0, num=1, withscores=True
    )
    stub_result = stub_redis_client.zrevrangebyscore(
        "reverse-index", 25, float("-inf"), start=0, num=1, withscores=True
    )
    assert real_result == stub_result == [("middle", 20.0)]


def test_scan_iter_hash_excludes_timeseries(real_redis_client, stub_redis_client):
    real_redis_client.hset("current-value", mapping={"value": "1"})
    stub_redis_client.hset("current-value", mapping={"value": "1"})
    real_redis_client.execute_command("TS.CREATE", "history")
    stub_redis_client.execute_command("TS.CREATE", "history")

    real_result = sorted(real_redis_client.scan_iter(_type="hash"))
    stub_result = sorted(stub_redis_client.scan_iter(_type="hash"))

    assert real_result == stub_result == ["current-value"]

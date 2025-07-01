# This file verifies the stub implementation of the RedisClient class.
# If later this is included in the automated tests we would need to deploy a Redis server.
# For now, we can manually run this file to verify the stub implementation.

import pytest
from nicos.services.cache.endpoints.redis_client import RedisClient
from test.test_cache.test_redis import RedisClientStub


@pytest.fixture(scope="module")
def real_redis_client():
    client = RedisClient(host="localhost", port=6379, db=0)
    client.execute_command("FLUSHALL")
    yield client
    client.close()


@pytest.fixture(scope="module")
def stub_redis_client():
    client = RedisClientStub()
    yield client


def test_hset_hgetall(real_redis_client, stub_redis_client):
    key = "test_key"
    mapping = {"field1": "value1", "field2": "value2"}

    real_redis_client.hset(key, mapping)
    stub_redis_client.hset(key, mapping)

    real_data = real_redis_client.hgetall(key)
    stub_data = stub_redis_client.hgetall(key)

    assert real_data == stub_data


def test_exists(real_redis_client, stub_redis_client):
    key = "test_exists_key"
    mapping = {"field1": "value1"}

    real_redis_client.hset(key, mapping)
    stub_redis_client.hset(key, mapping)

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
        real_redis_client.hset(key, mapping)
        stub_redis_client.hset(key, mapping)

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

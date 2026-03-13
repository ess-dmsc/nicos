import logging
from functools import wraps

import redis
from redis.exceptions import RedisError as DefaultRedisError


class RedisError(DefaultRedisError):
    pass


def handle_redis_errors(default_return=None, custom_message="", exception=RedisError):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception as e:
                logging.exception(f"{custom_message}: {e}")
                return default_return

        return wrapper

    return decorator


class RedisClient:
    def __init__(self, host, port, db, injected_redis=None):
        self._redis = self._setup(host, port, db, injected_redis)

    def _setup(self, host, port, db, injected_redis):
        if injected_redis:
            return injected_redis
        return redis.StrictRedis(host=host, port=port, db=db, decode_responses=True)

    @handle_redis_errors(
        default_return={}, custom_message="Failed to get data from Redis"
    )
    def hgetall(self, key):
        return self._redis.hgetall(key)

    @handle_redis_errors(
        default_return=[],
        custom_message="Failed to get multiple hash fields from Redis",
    )
    def hmget(self, key, *fields):
        if len(fields) == 1 and isinstance(fields[0], (list, tuple)):
            return self._redis.hmget(key, fields[0])
        return self._redis.hmget(key, *fields)

    @handle_redis_errors(custom_message="Failed to set data in Redis")
    def hset(self, name, key=None, value=None, mapping=None, items=None):
        return self._redis.hset(
            name, key=key, value=value, mapping=mapping, items=items
        )

    @handle_redis_errors(
        default_return=0, custom_message="Failed to add members to sorted set in Redis"
    )
    def zadd(self, name, mapping, *args, **kwargs):
        return self._redis.zadd(name, mapping, *args, **kwargs)

    @handle_redis_errors(
        default_return=[],
        custom_message="Failed to retrieve zrange by score from Redis",
    )
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
        return self._redis.zrangebyscore(
            name,
            min,
            max,
            start=start,
            num=num,
            withscores=withscores,
            score_cast_func=score_cast_func,
        )

    @handle_redis_errors(
        default_return=0, custom_message="Failed to check existence of key in Redis"
    )
    def exists(self, key):
        return self._redis.exists(key)

    @handle_redis_errors(custom_message="Failed to execute command in Redis")
    def execute_command(self, command, *args):
        return self._redis.execute_command(command, *args)

    @handle_redis_errors(
        default_return=[], custom_message="Failed to retrieve keys from Redis"
    )
    def keys(self):
        return self._redis.keys()

    @handle_redis_errors(
        default_return=None, custom_message="Failed to create pubsub object in Redis"
    )
    def pubsub(self):
        return self._redis.pubsub()

    def close(self):
        self._redis.close()

    def shutdown(self):
        self._redis.shutdown()

    @handle_redis_errors(
        default_return=iter(()), custom_message="Failed during SCAN iteration"
    )
    def scan_iter(self, *args, **kwargs):
        return self._redis.scan_iter(*args, **kwargs)

    @handle_redis_errors(
        default_return=None, custom_message="Failed to create pipeline"
    )
    def pipeline(self, *args, **kwargs):
        return self._redis.pipeline(*args, **kwargs)

    @handle_redis_errors(
        default_return=None, custom_message="Failed to execute script in Redis"
    )
    def script_load(self, script):
        return self._redis.script_load(script)

    @handle_redis_errors(
        default_return=None, custom_message="Failed to execute Lua script in Redis"
    )
    def evalsha(self, sha, numkeys=0, *keys_and_args):
        return self._redis.evalsha(sha, numkeys, *keys_and_args)

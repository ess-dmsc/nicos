"""Redis-backed NICOS cache database"""

from __future__ import annotations

import ast
import threading
import time
from typing import Dict, List, Tuple

from nicos.core import Param
from nicos.services.cache.database import CacheDatabase
from nicos.services.cache.endpoints.redis_client import RedisClient
from nicos.services.cache.entry import CacheEntry
from nicos.utils import createThread

KeyTuple = Tuple[str, str]


CLEANER_LUA = """
local now   = tonumber(ARGV[1])
local cursor = ARGV[2] and tonumber(ARGV[2]) or 0
local cleaned = 0
repeat
  local res = redis.call('SCAN', cursor, 'COUNT', 512)
  cursor = tonumber(res[1])
  for _, key in ipairs(res[2]) do
    -- skip time-series and snapshot helper keys
    if not key:match('_ts$') and not key:match('_snapshot$') then
      local ttl_str  = redis.call('HGET', key, 'ttl')
      local time_str = redis.call('HGET', key, 'time')
      local expired  = redis.call('HGET', key, 'expired')

      if ttl_str and ttl_str ~= 'None' and expired == 'False' then
        local ttl = tonumber(ttl_str)
        local t0  = tonumber(time_str)
        if ttl and t0 and (t0 + ttl) < now then
          redis.call('HSET', key, 'expired', 'True')
          cleaned = cleaned + 1
        end
      end
    end
  end
until cursor == 0
return cleaned
"""


class RedisCacheDatabase(CacheDatabase):
    parameters = {
        "host": Param("Redis host", type=str, default="localhost"),
        "port": Param("Redis port", type=int, default=6379),
        "db": Param("Redis DB", type=int, default=0),
    }

    _write_lock = threading.Lock()
    _snapshot_lock = threading.Lock()
    _snapshot_ready = threading.Event()
    _snapshot_data: List[Tuple[KeyTuple, CacheEntry]] = []
    _snapshot_time = 0.0
    _snapshot_building = False
    _SNAPSHOT_TTL = 5.0

    def doInit(self, mode: str, injected_client: RedisClient | None = None):
        self._client = injected_client or RedisClient(
            host=self.host, port=self.port, db=self.db
        )
        CacheDatabase.doInit(self, mode)

        self._stoprequest = False
        self._cleaner = self._start_cleaner()

    def doShutdown(self):
        self._stoprequest = True
        self._client.close()
        self._cleaner.join()

    def _start_cleaner(self):
        lua_sha = self._client.script_load(CLEANER_LUA)

        def _tick():
            while not self._stoprequest:
                time.sleep(self._long_loop_delay)
                try:
                    cleaned = self._client.evalsha(lua_sha, 0, time.time())
                    if cleaned:
                        self.log.warn("Redis cleaner: marked %s keys expired", cleaned)
                except Exception:
                    self.log.exception("Redis cleaner failed")

        return createThread("redis-cleaner", _tick)

    def _literal_or_str(self, val: str):
        try:
            parsed = ast.literal_eval(val)
            return parsed if isinstance(parsed, (int, float)) else val
        except Exception:
            return val

    def _hash_set(self, key, time, ttl, value, expired):
        self._client.hset(
            key,
            mapping={
                "time": str(time),
                "ttl": str(ttl),
                "value": str(value),
                "expired": str(expired),
            },
        )

    def _hash_getall(self, key):
        return self._client.hgetall(key)

    def _redis_key_exists(self, key):
        return self._client.exists(key)

    def _create_timeseries(self, key):
        self._client.execute_command("TS.CREATE", key, "DUPLICATE_POLICY", "LAST")

    def _add_to_timeseries(self, key, timestamp, value):
        self._client.execute_command("TS.ADD", key, timestamp, value)

    def _query_timeseries(self, key, fromtime, totime, *args):
        return self._client.execute_command("TS.RANGE", key, fromtime, totime, *args)

    def _redis_keys(self):
        return self._client.keys()

    def _redis_pubsub(self):
        return self._client.pubsub()

    def _check_get_key_format(self, key):
        return "###" not in key and not key.endswith("_ts")

    def _format_key(self, category, subkey):
        key = subkey if category == "nocat" else f"{category}/{subkey}"
        return key, f"{key}_ts"

    def _entry_from_hash(self, h: Dict[str, str] | None):
        if not h or not {"time", "ttl", "value"}.issubset(h):
            return None

        if h.get("value", "") == "":
            return None

        ttl = None if h["ttl"] == "None" else self._literal_or_str(h["ttl"])
        expired = True if h.get("expired", "False") == "True" else False
        entry = CacheEntry(
            self._literal_or_str(h["time"]), ttl, self._literal_or_str(h["value"])
        )
        entry.expired = expired
        return entry

    def _flush(self, keys: List[str], raws: List[Dict[str, str]]):
        for k, h in zip(keys, raws):
            entry = self._entry_from_hash(h)
            if not entry:
                continue
            cat, sub = k.rsplit("/", 1) if "/" in k else ("nocat", k)
            yield (cat, sub), entry

    def _get_data(self, key):
        if not self._check_get_key_format(key):
            self.log.debug(f"Invalid key format: {key}")
            return None
        return self._entry_from_hash(self._hash_getall(key))

    def getEntry(self, dbkey):
        redis_key, _ = self._format_key(dbkey[0], dbkey[1])
        return self._get_data(redis_key)

    def iterEntries(self, batch: int = 512):
        cls = self.__class__

        if (
            cls._snapshot_ready.is_set()
            and time.time() - cls._snapshot_time < cls._SNAPSHOT_TTL
        ):
            yield from cls._snapshot_data
            return

        with cls._snapshot_lock:
            if (
                cls._snapshot_ready.is_set()
                and time.time() - cls._snapshot_time < cls._SNAPSHOT_TTL
            ):
                yield from cls._snapshot_data
                return

            if cls._snapshot_building:
                waiter = True
            else:
                cls._snapshot_building = True
                cls._snapshot_ready.clear()
                waiter = False

        if waiter:
            cls._snapshot_ready.wait()
            yield from cls._snapshot_data
            return

        try:
            data = list(self._iter_entries_stream(batch))
            with cls._snapshot_lock:
                cls._snapshot_data = data
                cls._snapshot_time = time.time()
                cls._snapshot_ready.set()
        finally:
            cls._snapshot_building = False

        yield from data

    def _iter_entries_stream(self, batch):
        buf, pipe = [], None
        for key in self._client.scan_iter(count=batch):
            if not self._check_get_key_format(key):
                continue
            buf.append(key)
            if pipe is None:
                pipe = self._client.pipeline(transaction=False)
            pipe.hgetall(key)
            if len(buf) == batch:
                yield from self._flush(buf, pipe.execute())
                buf, pipe = [], None
        if buf and pipe is not None:
            yield from self._flush(buf, pipe.execute())

    def updateEntries(self, categories, subkey, _no_store, entry):
        with self._write_lock:
            pipe = self._client.pipeline(transaction=False)
            for cat in categories:
                self._set_data(cat, subkey, entry, pipe)
            pipe.execute()
        return True

    def queryHistory(self, dbkey, fromtime, totime, interval=None):
        _, ts_key = self._format_key(dbkey[0], dbkey[1])

        from_ms = int(fromtime * 1000)
        to_ms = int(totime * 1000)

        try:
            if interval:
                res = self._query_timeseries(
                    ts_key, from_ms, to_ms, "AGGREGATION", "avg", int(interval * 1000)
                )
            else:
                res = self._query_timeseries(ts_key, from_ms, to_ms)

        except Exception as e:
            self.log.warn(f"queryHistory: TS.RANGE failed for {ts_key}: {e}")
            return []

        def _ts_entry(ts, val):
            return CacheEntry(ts / 1000.0, None, ast.literal_eval(val))

        return list(map(lambda p: _ts_entry(*p), res))

    def _set_data(self, category, subkey, entry, pipe=None):
        if type(entry.value) not in (int, float, str, list, dict, type(None)):
            self.log.warning("Unsupported value type: %s", type(entry.value))
            return
        if not isinstance(self._literal_or_str(entry.time), (float, int)):
            self.log.warning("Unsupported time type: %s", type(entry.time))
            return
        if "*" in subkey or "###" in subkey:
            self.log.debug("Subkey ignored contains: %s", subkey)
            return

        redis_key, ts_key = self._format_key(category, subkey)
        target = pipe or self._client

        if entry.value in ("", None):
            target.execute_command("DEL", redis_key)
            if self._redis_key_exists(ts_key):
                target.execute_command("DEL", ts_key)
            return

        target.hset(
            redis_key,
            mapping={
                "time": str(entry.time),
                "ttl": str(entry.ttl),
                "value": str(entry.value),
                "expired": str(entry.expired),
            },
        )
        value = self._literal_or_str(entry.value)
        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if isinstance(value, (float, int)) and not isinstance(value, bool):
            val = value
            ts = int(float(entry.time) * 1000)
            if not self._redis_key_exists(ts_key):
                target.execute_command("TS.CREATE", ts_key, "DUPLICATE_POLICY", "LAST")
            target.execute_command("TS.ADD", ts_key, ts, val)

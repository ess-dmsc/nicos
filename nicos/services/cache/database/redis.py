"""Redis-backed NICOS cache database with in-memory front (self._recent)."""

from __future__ import annotations

import math
import threading
import time
from typing import Dict, Iterable, List, Optional, Tuple, Union

from nicos.core import Param
from nicos.protocols.cache import cache_load
from nicos.services.cache.database.base import CacheDatabase
from nicos.services.cache.endpoints.redis_client import RedisClient, RedisError
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
    """Cache database that persists to Redis but serves reads from RAM.

    Layout in Redis (unchanged):
      - One hash per value: "<category>/<subkey>" (or "<subkey>" if nocat)
        fields: time, ttl, value, expired ("True"/"False" as strings)
      - Optional RedisTimeSeries per numeric value: "<key>_ts"
    """

    parameters = {
        "host": Param("Redis host", type=str, default="localhost"),
        "port": Param("Redis port", type=int, default=6379),
        "db": Param("Redis DB", type=int, default=0),
    }

    def doInit(self, mode: str, injected_client: Union[RedisClient, None] = None):
        # in-memory current-value store: {category: [None, Lock(), {subkey: CacheEntry}]}
        self._recent: Dict[
            str, List[Union[None, threading.Lock, Dict[str, CacheEntry]]]
        ] = {}
        self._recent_lock = threading.Lock()

        self._client = injected_client or RedisClient(
            host=self.host, port=self.port, db=self.db
        )
        self._write_lock = threading.Lock()

        CacheDatabase.doInit(self, mode)

        # Prefill in-memory state from Redis once (via SCAN + pipelined HGETALL).
        self.initDatabase()

        # Background TTL cleaner using Lua in Redis; we also update RAM flags locally.
        self._stoprequest = False
        self._cleaner = self._start_cleaner()

    def doShutdown(self):
        self._stoprequest = True
        try:
            if hasattr(self, "_cleaner"):
                self._cleaner.join()
        finally:
            self._client.close()

    def _literal_or_str(self, val: str):
        try:
            parsed = cache_load(val)
            return parsed if isinstance(parsed, (int, float)) else val
        except Exception:
            return val

    def _hash_set(self, key, time_value, ttl, value, expired, target=None):
        t = target or self._client
        t.hset(
            key,
            mapping={
                "time": str(time_value),
                "ttl": str(ttl),
                "value": str(value),
                "expired": str(expired),
            },
        )

    def _hash_getall(self, key, target=None):
        t = target or self._client
        return t.hgetall(key)

    def _redis_key_exists(self, key, target=None):
        # NOTE: usually call without target inside write paths to avoid pipelining EXISTS.
        t = target or self._client
        return t.exists(key)

    def _create_timeseries(self, key, target=None):
        (target or self._client).execute_command(
            "TS.CREATE", key, "DUPLICATE_POLICY", "LAST"
        )

    def _add_to_timeseries(self, key, timestamp, value, target=None):
        (target or self._client).execute_command("TS.ADD", key, timestamp, value)

    def _query_timeseries(self, key, fromtime, totime, *args, target=None):
        return (target or self._client).execute_command(
            "TS.RANGE", key, fromtime, totime, *args
        )

    def _redis_keys(self, match="*", count=1024) -> Iterable[str]:
        return self._client.scan_iter(match=match, count=count)

    def _delete(self, key, target=None):
        (target or self._client).execute_command("DEL", key)

    def _check_get_key_format(self, key: str) -> bool:
        return "###" not in key and not key.endswith("_ts")

    def _format_key(self, category: str, subkey: str):
        key = subkey if category == "nocat" else f"{category}/{subkey}"
        return key, f"{key}_ts"

    def _entry_from_hash(self, h: Union[Dict[str, str], None]) -> Optional[CacheEntry]:
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

    def _normalize_entry(self, entry: CacheEntry) -> CacheEntry:
        """Ensure time/ttl are numeric (not strings) before storing in RAM."""
        t = entry.time
        tt = entry.ttl
        t_conv = self._literal_or_str(t) if isinstance(t, str) else t
        tt_conv = None
        if tt not in (None, "None"):
            tt_conv = self._literal_or_str(tt) if isinstance(tt, str) else tt

        norm = CacheEntry(t_conv, tt_conv, entry.value)
        norm.expired = entry.expired
        return norm

    def initDatabase(self, batch: int = 512):
        loaded = 0
        for (cat, sub), entry in self._iter_entries_stream(batch):
            # entry from _entry_from_hash already has numeric time/ttl
            self._set_recent(cat, sub, entry)
            loaded += 1
        self.log.info("RedisCacheDatabase: loaded %d current entries into RAM", loaded)

    def _iter_entries_stream(self, batch: int = 512):
        buf: List[str] = []
        pipe = None
        for key in self._redis_keys(count=batch):
            if not isinstance(key, str):
                try:
                    key = key.decode("utf-8")
                except Exception:
                    continue
            if not self._check_get_key_format(key):
                continue
            buf.append(key)
            if pipe is None:
                pipe = self._client.pipeline(transaction=False)
            self._hash_getall(key, target=pipe)
            if len(buf) == batch:
                try:
                    raws = pipe.execute()
                except Exception:
                    raws = [{} for _ in buf]
                yield from self._flush(buf, raws)
                buf, pipe = [], None
        if buf and pipe is not None:
            try:
                raws = pipe.execute()
            except Exception:
                raws = [{} for _ in buf]
            yield from self._flush(buf, raws)

    def _ensure_category(self, category: str):
        with self._recent_lock:
            if category not in self._recent:
                self._recent[category] = [None, threading.Lock(), {}]
            return self._recent[category]

    def _set_recent(self, category: str, subkey: str, entry: CacheEntry):
        _, lock, db = self._ensure_category(category)
        norm = self._normalize_entry(entry)
        with lock:
            db[subkey] = norm

    def _del_recent(self, category: str, subkey: str):
        with self._recent_lock:
            triple = self._recent.get(category)
        if not triple:
            return
        _, lock, db = triple
        with lock:
            db.pop(subkey, None)

    def getEntry(self, dbkey: KeyTuple):
        category, subkey = dbkey
        with self._recent_lock:
            triple = self._recent.get(category)
        if triple:
            _, lock, db = triple
            with lock:
                entry = db.get(subkey)
                if entry is not None:
                    return entry

        # Lazy fallback: if not in RAM (e.g., external writer), read once and cache.
        redis_key, _ = self._format_key(category, subkey)
        try:
            entry = self._get_data(redis_key)
        except Exception:
            entry = None
        if entry:
            self._set_recent(category, subkey, entry)
        return entry

    def iterEntries(self):
        # Iterate a snapshot of categories to avoid holding the big lock too long
        for cat, (_, lock, db) in list(self._recent.items()):
            with lock:
                for subkey, entry in db.items():
                    yield (cat, subkey), entry

    def queryHistory(self, dbkey, fromtime, totime, interval=None):
        category, subkey = dbkey
        redis_key, base_ts_key = self._format_key(category, subkey)

        from_ms = int(fromtime * 1000)
        to_ms = int(totime * 1000)

        # Read metadata describing how this value is archived in TS
        try:
            meta = self._hash_getall(redis_key)
        except Exception as e:
            self.log.warning(
                "queryHistory: failed to read metadata hash for %s: %s",
                redis_key,
                e,
            )
            meta = {}

        encoding = meta.get("ts_encoding")  # "scalar", "list", "dict", or None
        children_raw = meta.get("ts_children", "")
        children = [c for c in children_raw.split(",") if c] if children_raw else []

        def _range(ts_key: str):
            """Wrapper around TS.RANGE with optional aggregation."""
            try:
                if interval:
                    return self._query_timeseries(
                        ts_key,
                        from_ms,
                        to_ms,
                        "AGGREGATION",
                        "avg",
                        int(interval * 1000),
                    )
                else:
                    return self._query_timeseries(ts_key, from_ms, to_ms)
            except Exception as e:
                self.log.warning(
                    "queryHistory: TS.RANGE failed for %s: %s",
                    ts_key,
                    e,
                )
                return []

        if encoding == "list" and children:
            # children are indices for list positions
            try:
                indices = [int(c) for c in children]
            except ValueError:
                # corrupt metadata, fall back to scalar behaviour
                indices = []

            if not indices:
                res = _range(base_ts_key)
                return [
                    CacheEntry(ts / 1000.0, None, cache_load(val)) for ts, val in res
                ]

            ts_map: Dict[int, Dict[int, float]] = {}

            for idx in indices:
                ts_key = f"{redis_key}_l_{idx}_ts"
                samples = _range(ts_key)
                for ts, val in samples:
                    ts_int = int(ts)
                    # val may already be numeric in real RedisTimeSeries.
                    numeric = cache_load(val) if isinstance(val, str) else val
                    per_ts = ts_map.setdefault(ts_int, {})
                    per_ts[idx] = numeric

            entries: List[CacheEntry] = []
            for ts_int in sorted(ts_map.keys()):
                per_ts = ts_map[ts_int]
                # Reconstruct list in the original order of indices, padding missing with None
                reconstructed = [per_ts.get(idx, None) for idx in indices]
                entries.append(CacheEntry(ts_int / 1000.0, None, reconstructed))

            return entries

        if encoding == "dict" and children:
            keys = children[:]  # dict keys as strings

            ts_map: Dict[int, Dict[str, float]] = {}

            for key_name in keys:
                ts_key = f"{redis_key}_d_{key_name}_ts"
                samples = _range(ts_key)
                for ts, val in samples:
                    ts_int = int(ts)
                    numeric = cache_load(val) if isinstance(val, str) else val
                    per_ts = ts_map.setdefault(ts_int, {})
                    per_ts[key_name] = numeric

            entries: List[CacheEntry] = []
            for ts_int in sorted(ts_map.keys()):
                per_ts = ts_map[ts_int]
                # Only include keys that actually have values at this timestamp
                reconstructed = {k: per_ts[k] for k in keys if k in per_ts}
                entries.append(CacheEntry(ts_int / 1000.0, None, reconstructed))

            return entries

        res = _range(base_ts_key)

        def _ts_entry(ts, val):
            return CacheEntry(ts / 1000.0, None, cache_load(val))

        return [_ts_entry(ts, val) for ts, val in res]

    def updateEntries(
        self, categories: List[str], subkey: str, no_store: bool, entry: CacheEntry
    ):
        """Apply a logical update to one or more categories (due to rewrites)."""
        real_update = True
        # Normalize once (used both for RAM and to refresh TTL/time)
        ne = self._normalize_entry(entry)

        for cat in categories:
            # Ensure category structures
            _, lock, db = self._ensure_category(cat)

            update_needed = True
            with lock:
                if subkey in db:
                    curentry = db[subkey]
                    # same value and not expired: refresh time/ttl only
                    if curentry.value == ne.value and not curentry.expired:
                        curentry.time = ne.time
                        curentry.ttl = ne.ttl
                        update_needed = False
                        real_update = False
                    # delete (value None) but already expired: skip
                    elif ne.value is None and curentry.expired:
                        update_needed = False
                        real_update = False

                if update_needed:
                    db[subkey] = ne

            if update_needed and not no_store:
                # Persist to Redis (batched via pipeline per updateEntries call)
                with self._write_lock:
                    pipe = self._client.pipeline(transaction=False)
                    self._set_data(cat, subkey, ne, pipe=pipe)
                    try:
                        pipe.execute()
                    except Exception:
                        self.log.exception(
                            "Redis pipeline execute failed for %s/%s", cat, subkey
                        )

            if ne.value in ("", None) and update_needed:
                # Also remove from RAM if deletion
                self._del_recent(cat, subkey)

        return real_update

    def _get_data(self, key):
        """Fetch a single entry directly from Redis (used by tests)."""
        if not self._check_get_key_format(key):
            self.log.debug(f"Invalid key format: {key}")
            return None
        try:
            return self._entry_from_hash(self._hash_getall(key))
        except Exception:
            # Guard against Redis errors / corrupted data
            return None

    def _set_data(self, category, subkey, entry: CacheEntry, pipe=None):
        """Write a single entry to Redis (and update RAM) — signature unchanged for tests."""
        # Type checks (compat with old test expectations)
        if type(entry.value) not in (int, float, str, list, dict, type(None)):
            self.log.warning("Unsupported value type: %s", type(entry.value))
            return
        if not isinstance(self._literal_or_str(entry.time), (float, int)):
            self.log.warning("Unsupported time type: %s", type(entry.time))
            return
        if "*" in subkey or "###" in subkey:
            self.log.debug("Subkey ignored contains: %s", subkey)
            return

        redis_key, base_ts_key = self._format_key(category, subkey)
        target = pipe or self._client

        # Deletion
        if entry.value in ("", None):
            try:
                self._delete(redis_key, target=target)
                if self._redis_key_exists(base_ts_key):
                    self._delete(base_ts_key, target=target)
            except Exception:
                self.log.exception(
                    "Failed to delete keys %s and/or %s", redis_key, base_ts_key
                )
            # Keep RAM in sync
            self._del_recent(category, subkey)
            return

        # --- Decide how to archive the value in TS ---------------------------------
        # Normalize value just for archiving decisions (hash always stores str(value))
        value = (
            self._literal_or_str(entry.value)
            if isinstance(entry.value, str)
            else entry.value
        )

        ts = int(float(entry.time) * 1000)

        ts_values: List[float] = []
        ts_keys: List[str] = []
        ts_encoding: Optional[str] = None  # "list" or "dict" only
        ts_children: Optional[str] = None  # comma-separated indices or keys

        if self._native_archiving(value):
            # Simple scalar numeric value — no metadata needed
            ts_values.append(value)
            ts_keys.append(base_ts_key)

        else:
            # Complex type: try list-of-numbers or dict-of-numbers
            if (
                isinstance(value, list)
                and value
                and all(self._native_archiving(v) for v in value)
            ):
                ts_encoding = "list"
                indices = list(range(len(value)))
                ts_children = ",".join(str(i) for i in indices)

                for idx, val in enumerate(value):
                    ts_keys.append(f"{redis_key}_l_{idx}_ts")
                    ts_values.append(val)

            elif (
                isinstance(value, dict)
                and value
                and all(self._native_archiving(v) for v in value.values())
            ):
                ts_encoding = "dict"
                # Keep keys in stable order
                keys = list(value.keys())
                ts_children = ",".join(str(k) for k in keys)

                for subk in keys:
                    val = value[subk]
                    ts_keys.append(f"{redis_key}_d_{subk}_ts")
                    ts_values.append(val)
            else:
                ts_values = []
                ts_keys = []

        hash_mapping = {
            "time": str(entry.time),
            "ttl": str(entry.ttl),
            "value": str(entry.value),
            "expired": str(entry.expired),
        }
        if ts_encoding is not None:
            hash_mapping["ts_encoding"] = ts_encoding
        if ts_children is not None:
            hash_mapping["ts_children"] = ts_children

        try:
            target.hset(redis_key, mapping=hash_mapping)
        except Exception:
            self.log.exception("Redis HSET failed for %s", redis_key)
            # Still update RAM so reads are immediate
            self._set_recent(category, subkey, entry)
            return

        # Update RAM to mirror current value immediately (normalized)
        self._set_recent(category, subkey, entry)

        for series_key, sample in zip(ts_keys, ts_values):
            try:
                if not self._redis_key_exists(series_key):
                    self._create_timeseries(series_key, target=target)
                self._add_to_timeseries(series_key, ts, sample, target=target)
            except Exception:
                self.log.exception(
                    "TS write failed for %s. Got type %s", series_key, type(sample)
                )

    def _native_archiving(self, value):
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            if math.isfinite(value):
                return True
        return False

    def _start_cleaner(self):
        lua_sha = self._client.script_load(CLEANER_LUA)

        def _tick():
            while not self._stoprequest:
                time.sleep(self._long_loop_delay)
                try:
                    cleaned = self._client.evalsha(lua_sha, 0, time.time())
                    if cleaned:
                        self.log.debug("Redis cleaner: marked %s keys expired", cleaned)
                except Exception:
                    self.log.exception("Redis cleaner failed")

                # Always sync RAM flags (cheap, no Redis writes here)
                try:
                    self._sync_ram_expired_flags()
                except Exception:
                    self.log.exception("Redis RAM flag sync failed")

        return createThread("redis-cleaner", _tick)

    def _sync_ram_expired_flags(self):
        """Mark entries as expired in RAM when their TTL has elapsed.
        This mirrors the Lua cleaner's behavior locally without writing back."""
        now = time.time()
        for _, lock, db in list(self._recent.values()):
            with lock:
                for entry in db.values():
                    if not entry.value or entry.expired:
                        continue
                    ttl = entry.ttl
                    if ttl and (entry.time + ttl < now):
                        entry.expired = True

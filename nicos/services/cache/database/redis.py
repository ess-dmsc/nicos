"""Redis-backed NICOS cache database with in-memory front (self._recent)."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Iterable

from nicos.core import Param, floatrange, intrange, none_or
from nicos.protocols.cache import cache_load
from nicos.services.cache.database.base import CacheDatabase
from nicos.services.cache.endpoints.redis_client import RedisClient
from nicos.services.cache.entry import CacheEntry

KeyTuple = tuple[str, str]


class RedisCacheDatabase(CacheDatabase):
    """Cache database that persists to Redis but serves reads from RAM.

    Layout in Redis:
      - One hash per value: "<category>/<subkey>" (or "<subkey>" if nocat)
        fields: time, ttl, value
      - RedisTimeSeries for finite scalar values and numeric components
      - Optional arbitrary-value history in a sorted set: "<key>_hs"
    """

    parameters = {
        "host": Param("Redis host", type=str, default="localhost"),
        "port": Param("Redis port", type=int, default=6379),
        "db": Param("Redis DB", type=int, default=0),
        "historydays": Param(
            "Maximum RedisTimeSeries history retention in days (0 disables pruning)",
            type=floatrange(0),
            default=14.0,
        ),
        "arbitraryhistorydays": Param(
            "Maximum arbitrary-value history retention in days "
            "(None disables arbitrary history, 0 disables pruning)",
            type=none_or(floatrange(0)),
            default=None,
        ),
        "maxnativecomponents": Param(
            "Maximum numeric components archived with RedisTimeSeries",
            type=intrange(1, 10000),
            default=50,
        ),
    }

    def doInit(self, mode: str, injected_client: RedisClient | None = None):
        self._recent: dict[KeyTuple, CacheEntry] = {}
        self._recent_lock = threading.RLock()
        self._layouts: dict[str, tuple] = {}

        self._client = injected_client or RedisClient(
            host=self.host, port=self.port, db=self.db
        )
        self._write_lock = threading.Lock()

        CacheDatabase.doInit(self, mode)

        # Prefill in-memory state from Redis once (via SCAN + pipelined HGETALL).
        self.initDatabase()

    def doShutdown(self):
        self._client.close()

    def initDatabase(self, batch: int = 512):
        loaded = 0
        for (cat, sub), entry in self._iter_entries_stream(batch):
            self._set_recent(cat, sub, entry)
            loaded += 1
        self.log.info("RedisCacheDatabase: loaded %d current entries into RAM", loaded)

    def getEntry(self, dbkey: KeyTuple):
        category, subkey = dbkey
        with self._recent_lock:
            entry = self._recent.get(dbkey)
            if entry is not None:
                self._refresh_expired_flag(entry)
                return entry

        redis_key = self._redis_key(category, subkey)
        try:
            entry = self._get_data(redis_key)
        except Exception:
            entry = None
        if entry:
            self._set_recent(category, subkey, entry)
        return entry

    def iterEntries(self):
        with self._recent_lock:
            now = time.time()
            items = list(self._recent.items())
            for _, entry in items:
                self._refresh_expired_flag(entry, now)
        yield from items

    def updateEntries(
        self, categories: list[str], subkey: str, no_store: bool, entry: CacheEntry
    ):
        """Apply a logical update to one or more categories (due to rewrites)."""
        entry = self._normalize_entry(entry)
        self._refresh_expired_flag(entry)
        real_update = True
        persist = []
        for category in categories:
            changed, should_persist = self._apply_recent_update(
                (category, subkey), entry
            )
            real_update = real_update and changed
            if should_persist and not no_store:
                persist.append((category, subkey, entry))
        self._persist_entries(persist)
        return real_update

    def queryHistory(self, dbkey, fromtime, totime, interval=None):
        category, subkey = dbkey
        redis_key = self._redis_key(category, subkey)
        from_ms = int(fromtime * 1000)
        to_ms = int(totime * 1000)
        layout = self._layouts.get(redis_key)
        if not layout:
            return []
        if layout[0] == "arbitrary":
            return self._query_arbitrary_history(
                self._arbitrary_key(redis_key), fromtime, totime, interval
            )
        return self._query_native_history(
            redis_key, subkey, layout, from_ms, to_ms, interval
        )

    def _hash_getall(self, key, target=None):
        t = target or self._client
        return t.hgetall(key)

    def _add_timeseries(self, key, timestamp, value, target=None):
        cmd = ["TS.ADD", key, timestamp, value]
        retention_ms = self._timeseries_retention_ms()
        if retention_ms is not None:
            cmd.extend(["RETENTION", retention_ms])
        cmd.extend(["DUPLICATE_POLICY", "LAST"])
        (target or self._client).execute_command(*cmd)

    def _query_ranges(self, keys, fromtime, totime, *args):
        pipe = self._client.pipeline(transaction=False)
        if pipe is None:
            return [[] for _ in keys]
        for key in keys:
            pipe.execute_command("TS.RANGE", key, fromtime, totime, *args)
        if fromtime > 0:
            for key in keys:
                pipe.execute_command("TS.REVRANGE", key, 0, fromtime - 1, "COUNT", 1)
        try:
            results = pipe.execute()
        except Exception as e:
            self.log.warning("RedisTimeSeries query failed: %s", e)
            return [[] for _ in keys]
        current = results[: len(keys)]
        if fromtime <= 0:
            return current
        return [results[len(keys) + i] + samples for i, samples in enumerate(current)]

    def _redis_keys(self, match="*", count=1024, _type=None) -> Iterable[str]:
        return self._client.scan_iter(match=match, count=count, _type=_type)

    def _delete(self, *keys, target=None):
        if keys:
            # History hashes can be very large. UNLINK removes their names
            # immediately while reclaiming memory outside Redis' main thread.
            (target or self._client).execute_command("UNLINK", *keys)

    @staticmethod
    def _retention_ms(days) -> int | None:
        if days is None:
            return None
        try:
            days = float(days)
        except Exception:
            return None
        if days <= 0:
            return None
        return max(1, int(days * 86400 * 1000))

    def _timeseries_retention_ms(self) -> int | None:
        return self._retention_ms(self.historydays)

    def _arbitrary_history_enabled(self) -> bool:
        return self.arbitraryhistorydays is not None

    def _arbitrary_retention_ms(self) -> int | None:
        return self._retention_ms(self.arbitraryhistorydays)

    def _check_get_key_format(self, key: str) -> bool:
        return "###" not in key

    @staticmethod
    def _redis_key(category: str, subkey: str):
        return subkey if category == "nocat" else f"{category}/{subkey}"

    @staticmethod
    def _arbitrary_key(redis_key: str):
        return f"{redis_key}_hs"

    def _classify_history(self, subkey: str, value):
        status_code = self._status_code(subkey, value)
        if status_code is not None:
            return ("status",), (status_code,)
        if self._is_native_number(value):
            return ("scalar",), (value,)
        components = self._numeric_components(value)
        if components is not None:
            return components
        return ("arbitrary",), ()

    def _status_code(self, subkey, value):
        if (
            subkey == "status"
            and isinstance(value, tuple)
            and len(value) == 2
            and type(value[0]) is int
            and isinstance(value[1], str)
            and self._is_native_number(value[0])
        ):
            return value[0]
        return None

    def _numeric_components(self, value):
        if isinstance(value, dict):
            layout = ("dict", tuple(value))
            components = tuple(value.values())
        elif isinstance(value, tuple):
            layout = ("tuple", len(value))
            components = value
        elif isinstance(value, list):
            layout = ("list", len(value))
            components = tuple(value)
        else:
            return None
        if not components or len(components) > self.maxnativecomponents:
            return None
        if not all(self._is_native_number(component) for component in components):
            return None
        return layout, components

    def _history_keys(self, redis_key: str, layout):
        if not layout:
            return []
        kind = layout[0]
        if kind in ("scalar", "status"):
            return [f"{redis_key}_ts"]
        if kind == "arbitrary":
            return [self._arbitrary_key(redis_key)]
        try:
            count = len(layout[1]) if kind == "dict" else int(layout[1])
        except (IndexError, TypeError, ValueError):
            return []
        return [f"{redis_key}_ts_{i}" for i in range(count)]

    def _remove_history(self, redis_key: str, layout, target=None):
        keys = self._history_keys(redis_key, layout)
        if keys:
            self._delete(*keys, target=target)

    def _entry_from_hash(self, h: dict[str, str] | None) -> CacheEntry | None:
        if not h or not {"time", "value"}.issubset(h):
            return None
        if h.get("value", "") == "":
            return None
        try:
            timestamp = float(h["time"])
            ttl = float(h["ttl"]) if h.get("ttl") else None
        except (TypeError, ValueError):
            return None
        entry = CacheEntry(timestamp, ttl, h["value"])
        self._refresh_expired_flag(entry)
        return entry

    def _flush(self, keys: list[str], raws: list[dict[str, str]]):
        for k, h in zip(keys, raws):
            entry = self._entry_from_hash(h)
            if not entry:
                continue
            cat, sub = k.rsplit("/", 1) if "/" in k else ("nocat", k)
            try:
                value = cache_load(entry.value)
            except Exception:
                self.log.warning("Invalid serialized cache value in %s", k)
                continue
            self._layouts[k] = self._classify_history(sub, value)[0]
            yield (cat, sub), entry

    def _normalize_entry(self, entry: CacheEntry) -> CacheEntry:
        """Ensure time and TTL are numeric before storing in RAM."""
        timestamp = float(entry.time)
        ttl = None if entry.ttl is None else float(entry.ttl)
        norm = CacheEntry(timestamp, ttl, entry.value)
        norm.expired = entry.expired
        return norm

    def _iter_entries_stream(self, batch: int = 512):
        buf: list[str] = []
        pipe = None
        for key in self._redis_keys(count=batch, _type="hash"):
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

    def _refresh_expired_flag(self, entry: CacheEntry, now: float | None = None):
        if entry.expired or entry.value in ("", None):
            return
        if not entry.ttl:
            return
        try:
            expired = entry.time + entry.ttl < (time.time() if now is None else now)
        except TypeError:
            return
        if expired:
            entry.expired = True

    def _set_recent(self, category: str, subkey: str, entry: CacheEntry):
        norm = self._normalize_entry(entry)
        self._refresh_expired_flag(norm)
        with self._recent_lock:
            self._recent[(category, subkey)] = norm

    @staticmethod
    def _arbitrary_member(timestamp, value):
        return f"{timestamp}:{value}"

    @staticmethod
    def _arbitrary_entries(samples):
        return [
            CacheEntry(timestamp / 1000.0, None, member.split(":", 1)[1])
            for member, timestamp in samples
        ]

    @staticmethod
    def _decimate_history(entries, fromtime, interval):
        result, next_boundary = [], None
        bucket_ms = int(interval * 1000)
        for entry in entries:
            timestamp = int(entry.time * 1000)
            if entry.time < fromtime:
                result.append(entry)
            elif next_boundary is None or timestamp >= next_boundary:
                result.append(entry)
                next_boundary = timestamp + bucket_ms
        return result

    def _query_arbitrary_history(self, key, fromtime, totime, interval):
        from_ms = int(fromtime * 1000)
        carry = []
        if from_ms > 0:
            carry = self._client.zrevrangebyscore(
                key,
                from_ms - 1,
                float("-inf"),
                start=0,
                num=1,
                withscores=True,
            )
        samples = carry + self._client.zrangebyscore(
            key, from_ms, int(totime * 1000), withscores=True
        )
        entries = self._arbitrary_entries(samples)
        return (
            self._decimate_history(entries, fromtime, interval) if interval else entries
        )

    @staticmethod
    def _native_range_options(kind, subkey, from_ms, interval):
        if not interval:
            return ()
        aggregation = (
            "max"
            if kind == "status"
            else "last"
            if subkey.endswith("limits")
            else "avg"
        )
        return "ALIGN", from_ms, "AGGREGATION", aggregation, int(interval * 1000)

    @staticmethod
    def _rebuild_history_value(layout, values):
        kind = layout[0]
        if kind == "status":
            return int(values[0]), None
        if kind == "scalar":
            return values[0]
        if kind == "dict":
            return dict(zip(layout[1], values))
        return tuple(values) if kind == "tuple" else values

    def _query_native_history(
        self, redis_key, subkey, layout, from_ms, to_ms, interval
    ):
        ranges = self._query_ranges(
            self._history_keys(redis_key, layout),
            from_ms,
            to_ms,
            *self._native_range_options(layout[0], subkey, from_ms, interval),
        )
        entries = []
        for samples in zip(*ranges):
            timestamps = {int(sample[0]) for sample in samples}
            if len(timestamps) != 1:
                continue
            values = [cache_load(sample[1]) for sample in samples]
            value = self._rebuild_history_value(layout, values)
            entries.append(CacheEntry(timestamps.pop() / 1000.0, None, value))
        return entries

    def _apply_recent_update(self, dbkey, entry):
        with self._recent_lock:
            current = self._recent.get(dbkey)
            if current is not None:
                self._refresh_expired_flag(current)
                if current.value == entry.value and not current.expired:
                    current.time, current.ttl = entry.time, entry.ttl
                    return False, True
                if entry.value is None and current.expired:
                    return False, False
            if entry.value is None:
                self._recent.pop(dbkey, None)
            else:
                self._recent[dbkey] = entry
            return True, True

    def _persist_entries(self, entries):
        if not entries:
            return
        with self._write_lock:
            pipe = self._client.pipeline(transaction=False)
            try:
                for category, subkey, entry in entries:
                    self._set_data(category, subkey, entry, pipe=pipe)
                if pipe is not None:
                    pipe.execute()
            except Exception:
                self.log.exception(
                    "Redis write pipeline failed for %d cache entries", len(entries)
                )

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

    def _valid_data_update(self, subkey, entry):
        if entry.value is not None and not isinstance(entry.value, str):
            self.log.warning("Unsupported value type: %s", type(entry.value))
            return False
        try:
            float(entry.time)
        except (TypeError, ValueError):
            self.log.warning("Unsupported time type: %s", type(entry.time))
            return False
        if "*" in subkey or "###" in subkey:
            self.log.debug("Subkey ignored contains: %s", subkey)
            return False
        return True

    def _delete_stored_entry(self, redis_key, target):
        self._remove_history(redis_key, self._layouts.pop(redis_key, ()), target=target)
        self._delete(redis_key, target=target)

    def _set_history_layout(self, redis_key, layout, target):
        old_layout = self._layouts.get(redis_key)
        if old_layout is not None and old_layout != layout:
            self._remove_history(redis_key, old_layout, target=target)
        self._layouts[redis_key] = layout

    def _store_arbitrary_history(self, key, timestamp, value, target):
        if not self._arbitrary_history_enabled():
            self._delete(key, target=target)
            return
        target.execute_command("ZREMRANGEBYSCORE", key, timestamp, timestamp)
        target.zadd(key, {self._arbitrary_member(timestamp, value): timestamp})
        retention = self._arbitrary_retention_ms()
        if retention is not None:
            target.execute_command(
                "ZREMRANGEBYSCORE", key, float("-inf"), timestamp - retention
            )

    def _set_data(self, category, subkey, entry: CacheEntry, pipe=None):
        """Write a single entry to Redis."""
        if not self._valid_data_update(subkey, entry):
            return

        redis_key = self._redis_key(category, subkey)
        target = pipe or self._client

        if entry.value is None:
            self._delete_stored_entry(redis_key, target)
            return

        try:
            value = cache_load(entry.value)
        except Exception:
            self.log.warning("Invalid serialized cache value for %s", redis_key)
            return
        layout, components = self._classify_history(subkey, value)
        self._set_history_layout(redis_key, layout, target)

        ts = int(float(entry.time) * 1000)
        target.hset(
            redis_key,
            mapping={
                "time": str(entry.time),
                "ttl": "" if entry.ttl is None else str(entry.ttl),
                "value": entry.value,
            },
        )

        if layout[0] == "arbitrary":
            self._store_arbitrary_history(
                self._arbitrary_key(redis_key), ts, entry.value, target
            )
            return

        for key, value in zip(self._history_keys(redis_key, layout), components):
            self._add_timeseries(key, ts, value, target=target)

    def _is_native_number(self, value):
        return (
            isinstance(value, (float, int))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

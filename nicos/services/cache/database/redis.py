"""Redis-backed NICOS cache database with in-memory front (self._recent)."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Iterable

from nicos.core import Param, floatrange, none_or
from nicos.protocols.cache import cache_load
from nicos.services.cache.database.base import CacheDatabase
from nicos.services.cache.endpoints.redis_client import RedisClient
from nicos.services.cache.entry import CacheEntry

KeyTuple = tuple[str, str]


class RedisCacheDatabase(CacheDatabase):
    """Cache database that persists to Redis but serves reads from RAM.

    Layout in Redis:
      - One hash per value: "<category>/<subkey>" (or "<subkey>" if nocat)
        fields: time, ttl, value, expired ("True"/"False" as strings)
      - Optional RedisTimeSeries per finite scalar numeric value: "<key>_ts"
      - Optional arbitrary-value history: "<key>_hs" plus "<key>_hs_idx"
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
    }

    def doInit(self, mode: str, injected_client: RedisClient | None = None):
        self._recent: dict[KeyTuple, CacheEntry] = {}
        self._recent_lock = threading.RLock()

        self._client = injected_client or RedisClient(
            host=self.host, port=self.port, db=self.db
        )
        self._write_lock = threading.Lock()

        CacheDatabase.doInit(self, mode)

        # Prefill in-memory state from Redis once (via SCAN + pipelined HGETALL).
        self.initDatabase()

    def doShutdown(self):
        self._client.close()

    def _literal_or_str(self, val: str):
        try:
            parsed = cache_load(val)
            return parsed if isinstance(parsed, (int, float)) else val
        except Exception:
            return val

    def _hash_getall(self, key, target=None):
        t = target or self._client
        return t.hgetall(key)

    def _redis_key_exists(self, key, target=None):
        # NOTE: usually call without target inside write paths to avoid pipelining EXISTS.
        t = target or self._client
        return t.exists(key)

    def _create_timeseries(self, key, target=None):
        cmd = ["TS.CREATE", key]
        retention_ms = self._timeseries_retention_ms()
        if retention_ms is not None:
            cmd.extend(["RETENTION", retention_ms])
        cmd.extend(["DUPLICATE_POLICY", "LAST"])
        (target or self._client).execute_command(*cmd)

    def _add_to_timeseries(self, key, timestamp, value, target=None):
        (target or self._client).execute_command("TS.ADD", key, timestamp, value)

    def _query_timeseries(self, key, fromtime, totime, *args, target=None):
        return (target or self._client).execute_command(
            "TS.RANGE", key, fromtime, totime, *args
        )

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

    def _hash_series_enabled(self) -> bool:
        return self.arbitraryhistorydays is not None

    def _hash_series_retention_ms(self) -> int | None:
        return self._retention_ms(self.arbitraryhistorydays)

    @staticmethod
    def _history_cutoff_ms(newest_ts_ms: int, retention_ms: int | None) -> int | None:
        if retention_ms is None:
            return None
        return int(newest_ts_ms - retention_ms)

    def _prune_timeseries(self, ts_key: str, newest_ts_ms: int, target=None):
        cutoff = self._history_cutoff_ms(newest_ts_ms, self._timeseries_retention_ms())
        if cutoff is None:
            return
        (target or self._client).execute_command("TS.DEL", ts_key, 0, cutoff)

    def _prune_hash_series(
        self, hs_hash_key: str, hs_idx_key: str, newest_ts_ms: int, target=None
    ):
        cutoff = self._history_cutoff_ms(newest_ts_ms, self._hash_series_retention_ms())
        if cutoff is None:
            return

        try:
            stale_fields = self._client.zrangebyscore(hs_idx_key, float("-inf"), cutoff)
        except Exception:
            self.log.exception(
                "hash_series prune index lookup failed for %s", hs_idx_key
            )
            return

        if not stale_fields:
            return

        normalized = []
        for f in stale_fields:
            if isinstance(f, str):
                normalized.append(f)
            else:
                try:
                    normalized.append(f.decode("utf-8"))
                except Exception:
                    normalized.append(str(f))

        t = target or self._client
        t.execute_command("HDEL", hs_hash_key, *normalized)
        t.execute_command("ZREMRANGEBYSCORE", hs_idx_key, float("-inf"), cutoff)

    def _check_get_key_format(self, key: str) -> bool:
        return "###" not in key

    def _format_key(self, category: str, subkey: str):
        """
        Return Redis keys for main hash and associated TS structures.
        Returns: (main_key, ts_key, hs_key, hs_idx_key)
        """
        key = subkey if category == "nocat" else f"{category}/{subkey}"
        return key, f"{key}_ts", f"{key}_hs", f"{key}_hs_idx"

    def _entry_from_hash(self, h: dict[str, str] | None) -> CacheEntry | None:
        if not h or not {"time", "ttl", "value"}.issubset(h):
            return None
        if h.get("value", "") == "":
            return None

        ttl = None if h["ttl"] == "None" else self._literal_or_str(h["ttl"])
        expired = h.get("expired", "False") == "True"
        entry = CacheEntry(self._literal_or_str(h["time"]), ttl, h["value"])
        entry.expired = expired
        self._refresh_expired_flag(entry)
        return entry

    def _flush(self, keys: list[str], raws: list[dict[str, str]]):
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
        buf: list[str] = []
        pipe = None
        for key in self._redis_keys(count=batch, _type="hash"):
            if not isinstance(key, str):
                try:
                    key = key.decode("utf-8")
                except Exception:
                    continue
            # Arbitrary histories are hashes too, but never current entries.
            # Fetching them with HGETALL can consume hundreds of MB at startup.
            if key.endswith("_hs") or not self._check_get_key_format(key):
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

    def _del_recent(self, category: str, subkey: str):
        with self._recent_lock:
            self._recent.pop((category, subkey), None)

    def getEntry(self, dbkey: KeyTuple):
        category, subkey = dbkey
        with self._recent_lock:
            entry = self._recent.get(dbkey)
            if entry is not None:
                self._refresh_expired_flag(entry)
                return entry

        # Lazy fallback: if not in RAM (e.g., external writer), read once and cache.
        redis_key, _, _, _ = self._format_key(category, subkey)
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

    def queryHistory(self, dbkey, fromtime, totime, interval=None):
        category, subkey = dbkey
        redis_key, base_ts_key, hs_hash_key, hs_idx_key = self._format_key(
            category, subkey
        )

        from_ms = int(fromtime * 1000)
        to_ms = int(totime * 1000)

        # Read metadata describing how this value is archived.
        try:
            meta = self._hash_getall(redis_key)
        except Exception as e:
            self.log.warning(
                "queryHistory: failed to read metadata hash for %s: %s",
                redis_key,
                e,
            )
            meta = {}

        encoding = meta.get("ts_encoding")

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

        if encoding == "hash_series":
            try:
                # 1) Get all timestamps in range, sorted by time
                ts_fields = self._client.zrangebyscore(hs_idx_key, from_ms, to_ms)
            except Exception as e:
                self.log.warning(
                    "queryHistory: failed to read hash_series index %s: %s",
                    hs_idx_key,
                    e,
                )
                return []

            if not ts_fields:
                return []

            try:
                # 2) Bulk fetch values for those timestamps
                values = self._client.hmget(hs_hash_key, *ts_fields)
            except Exception as e:
                self.log.warning(
                    "queryHistory: failed to HMGET hash_series %s: %s",
                    hs_hash_key,
                    e,
                )
                return []

            entries: list[CacheEntry] = []
            append = entries.append

            for ts_str, val_str in zip(ts_fields, values):
                if val_str is None:
                    # hash and zset out of sync; skip this sample
                    continue
                try:
                    ts_int = int(ts_str)
                except (TypeError, ValueError):
                    continue

                if not isinstance(val_str, str):
                    try:
                        val_str = val_str.decode("utf-8")
                    except Exception:
                        val_str = str(val_str)

                append(CacheEntry(ts_int / 1000.0, None, val_str))

            # Optional interval decimation – unchanged, we just decimate whole entries.
            if interval:
                bucket_ms = int(interval * 1000)
                if bucket_ms > 0 and len(entries) > 1:
                    bucketed: list[CacheEntry] = []
                    next_boundary = int(entries[0].time * 1000) + bucket_ms
                    bucketed_append = bucketed.append
                    bucketed_append(entries.pop(0))  # always include first entry
                    for e in entries:
                        t_ms = int(e.time * 1000)
                        if t_ms >= next_boundary:
                            bucketed_append(e)
                            next_boundary = t_ms + bucket_ms
                    return bucketed

            return entries

        res = _range(base_ts_key)

        def _ts_entry(ts, val):
            return CacheEntry(ts / 1000.0, None, cache_load(val))

        return list(map(lambda p: _ts_entry(*p), res))

    def updateEntries(
        self, categories: list[str], subkey: str, no_store: bool, entry: CacheEntry
    ):
        """Apply a logical update to one or more categories (due to rewrites)."""
        real_update = True
        # Normalize once (used both for RAM and to refresh TTL/time)
        ne = self._normalize_entry(entry)
        self._refresh_expired_flag(ne)
        persist_entries: list[tuple[str, str, CacheEntry]] = []

        for cat in categories:
            update_needed = True
            refresh_only = False
            dbkey = (cat, subkey)
            with self._recent_lock:
                if dbkey in self._recent:
                    curentry = self._recent[dbkey]
                    self._refresh_expired_flag(curentry)
                    # same value and not expired: refresh time/ttl only
                    if curentry.value == ne.value and not curentry.expired:
                        curentry.time = ne.time
                        curentry.ttl = ne.ttl
                        update_needed = False
                        refresh_only = True
                        real_update = False
                    # delete (value None) but already expired: skip
                    elif ne.value is None and curentry.expired:
                        update_needed = False
                        real_update = False

                if update_needed:
                    if ne.value in ("", None):
                        self._recent.pop(dbkey, None)
                    else:
                        self._recent[dbkey] = ne

            if (update_needed or refresh_only) and not no_store:
                persist_entries.append((cat, subkey, ne))

        if persist_entries:
            with self._write_lock:
                pipe = self._client.pipeline(transaction=False)
                try:
                    for cat, subkey, entry in persist_entries:
                        self._set_data(
                            cat, subkey, entry, pipe=pipe, update_recent=False
                        )
                    if pipe is not None:
                        pipe.execute()
                except Exception:
                    self.log.exception(
                        "Redis write pipeline failed for %d cache entries",
                        len(persist_entries),
                    )

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

    def _set_data(
        self, category, subkey, entry: CacheEntry, pipe=None, update_recent: bool = True
    ):
        """Write a single entry to Redis and update RAM."""
        # Type checks (compat with old test expectations)
        if type(entry.value) not in (int, float, str, list, tuple, dict, type(None)):
            self.log.warning("Unsupported value type: %s", type(entry.value))
            return
        if not isinstance(self._literal_or_str(entry.time), (float, int)):
            self.log.warning("Unsupported time type: %s", type(entry.time))
            return
        if "*" in subkey or "###" in subkey:
            self.log.debug("Subkey ignored contains: %s", subkey)
            return

        redis_key, base_ts_key, hs_hash_key, hs_idx_key = self._format_key(
            category, subkey
        )
        target = pipe or self._client

        # Deletion
        if entry.value in ("", None):
            self._delete(
                redis_key,
                base_ts_key,
                hs_hash_key,
                hs_idx_key,
                target=target,
            )
            if update_recent:
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

        ts_values: list[float] = []
        ts_keys: list[str] = []
        ts_encoding: str | None = None

        if self._native_archiving(value):
            # Simple scalar numeric value: native RedisTimeSeries, no metadata needed.
            ts_values.append(value)
            ts_keys.append(base_ts_key)

        else:
            ts_encoding = "hash_series"

        hash_mapping = {
            "time": str(entry.time),
            "ttl": str(entry.ttl),
            "value": str(entry.value),
            "expired": str(entry.expired),
        }
        if ts_encoding is not None:
            hash_mapping["ts_encoding"] = ts_encoding

        target.hset(redis_key, mapping=hash_mapping)

        stale_meta_fields = ["ts_children"]
        if ts_encoding is None:
            stale_meta_fields.append("ts_encoding")
        target.execute_command("HDEL", redis_key, *stale_meta_fields)

        # Update RAM to mirror current value immediately (normalized)
        if update_recent:
            self._set_recent(category, subkey, entry)

        for series_key, sample in zip(ts_keys, ts_values):
            if not self._redis_key_exists(series_key):
                self._create_timeseries(series_key, target=target)
            self._add_to_timeseries(series_key, ts, sample, target=target)
            self._prune_timeseries(series_key, ts, target=target)

        if ts_encoding == "hash_series":
            if not self._hash_series_enabled():
                # Reclaim history created before arbitrary archiving was disabled.
                self._delete(hs_hash_key, hs_idx_key, target=target)
                return

            ts_str = str(ts)
            target.hset(hs_hash_key, ts_str, str(value))
            target.zadd(hs_idx_key, {ts_str: ts})
            self._prune_hash_series(hs_hash_key, hs_idx_key, ts, target=target)

    def _native_archiving(self, value):
        return (
            isinstance(value, (float, int))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

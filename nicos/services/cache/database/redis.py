import logging
import threading

from nicos.core import Param
from nicos.services.cache.database import CacheDatabase
from nicos.services.cache.entry import CacheEntry
from nicos.services.cache.endpoints.redis_client import RedisClient


class RedisCacheDatabase(CacheDatabase):
    parameters = {
        "host": Param("Host of the Redis server", type=str, default="localhost"),
        "port": Param("Port of the Redis server", type=int, default=6379),
        "db": Param("Redis database number", type=int, default=0),
    }

    def doInit(self, mode, injected_client=None):
        self._db = {}
        self._db_lock = threading.Lock()
        self._client = (
            injected_client
            if injected_client
            else RedisClient(host=self.host, port=self.port, db=self.db)
        )
        self._redis_lock = threading.Lock()
        CacheDatabase.doInit(self, mode)

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

    def _query_timeseries(self, key, fromtime, totime):
        return self._client.execute_command("TS.RANGE", key, fromtime, totime)

    def _redis_keys(self):
        return self._client.keys()

    def _redis_pubsub(self):
        return self._client.pubsub()

    def _convert_to_number_if_possible(self, value):
        try:
            return float(value)
        except ValueError:
            return value
        except TypeError:
            return value

    def _format_key(self, category, subkey):
        key = subkey if category == "nocat" else f"{category}/{subkey}"
        return key, f"{key}_ts"

    def _check_get_key_format(self, key):
        if "###" in key:
            logging.debug(f"Key contains '###': {key}")
            return False

        if key.endswith("_ts"):
            logging.debug(f"Skipping time series key: {key}")
            return False

        if not self._redis_key_exists(key):
            logging.debug(f"Key does not exist: {key}")
            return False
        return True

    def _format_get_results(self, data):
        required_keys = ["time", "ttl", "value"]

        if not all(key in data for key in required_keys):
            logging.warning(f"Missing keys in data: {data}")
            return None

        if data["ttl"] == "None":
            data["ttl"] = None

        return CacheEntry(
            self._convert_to_number_if_possible(data.get("time", None)),
            self._convert_to_number_if_possible(data.get("ttl", None)),
            self._convert_to_number_if_possible(data.get("value", None)),
        )

    def _get_data(self, key):
        if not self._check_get_key_format(key):
            return None

        data = self._hash_getall(key)
        if not data:
            return None

        return self._format_get_results(data)

    def _set_data(self, category, subkey, entry):
        key, ts_key = self._format_key(category, subkey)

        if "*" in key:
            logging.warning(f"Wildcard in key: {key}")
            return

        if type(entry.value) not in [int, float, str, list, dict, type(None)]:
            logging.warning(f"Unsupported value type: {type(entry.value)}")
            return

        try:
            float(entry.time)
            if entry.ttl:
                float(entry.ttl)
        except ValueError:
            logging.warning(f"Invalid time: {entry.time} or ttl: {entry.ttl}")
            return

        time = entry.time if entry.time else str(entry.time)
        ttl = entry.ttl if entry.ttl else str(entry.ttl)
        value = entry.value if entry.value else str(entry.value)
        expired = entry.expired if entry.expired else str(entry.expired)

        self._hash_set(key, time, ttl, value, expired)

        try:
            numeric_value = float(value)
            timestamp = int(float(time) * 1000)

            if self._redis_key_exists(ts_key):
                self._add_to_timeseries(ts_key, timestamp, numeric_value)
            else:
                self._create_timeseries(ts_key)
                self._add_to_timeseries(ts_key, timestamp, numeric_value)
        except (ValueError, TypeError):
            logging.debug("Don't add timeseries because value is not numeric")

    def getEntry(self, dbkey):
        key, _ = self._format_key(dbkey[0], dbkey[1])
        with self._redis_lock:
            return self._get_data(key)

    def iterEntries(self):
        for key in self._redis_keys():
            with self._redis_lock:
                entry = self._get_data(key)
                if entry:
                    category, subkey = key.rsplit("/", 1)
                    yield (category, subkey), entry

    def updateEntries(self, categories, subkey, no_store, entry):
        real_update = True
        with self._redis_lock:
            for cat in categories:
                current_entry = self._get_data(f"{cat}/{subkey}")
                if current_entry:
                    if current_entry.value == entry.value and not current_entry.expired:
                        real_update = False
                    elif entry.value is None and current_entry.expired:
                        real_update = False
                if real_update:
                    self._set_data(cat, subkey, entry)
        return real_update

    def queryHistory(self, dbkey, fromtime, totime, interval=None):
        _, ts_key = self._format_key(dbkey[0], dbkey[1])

        if not self._redis_key_exists(ts_key):
            logging.debug(f"Time series key does not exist: {ts_key}")
            return []

        try:
            fromtime_ms = int(fromtime * 1000)
            totime_ms = int(totime * 1000)

            result = self._query_timeseries(ts_key, fromtime_ms, totime_ms)

            entries = [
                CacheEntry(float(data_point[0]) / 1000, None, float(data_point[1]))
                for data_point in result
            ]

            return entries

        except Exception as e:
            logging.exception(f"Failed to query history from Redis: {e}")
            return []

    def doShutdown(self):
        logging.info("Shutting down RedisCacheDatabase")
        self._client.shutdown()
        self._client.close()

# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Konstantin Kholostov <k.kholostov@fz-juelich.de>
#
# *****************************************************************************

import ast
import csv
from datetime import datetime
import threading

from influxdb_client import InfluxDBClient, BucketRetentionRules, Point
from influxdb_client.client.write_api import SYNCHRONOUS as write_option

from nicos.core import Param, ConfigurationError
from nicos.services.cache.database.base import CacheDatabase
from nicos.services.cache.entry import CacheEntry
from nicos.utils.credentials.keystore import nicoskeystore


csv.field_size_limit(0xA00000) # 10 MB limit for influx queries with big fields


class InfluxDBWrapper:
    """Wrapper for InfluxDB API 2.0.
    """

    def __init__(self, url, token, org, bucket):
        self._update_queue = []
        self._update_lock = threading.Lock()
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._client = InfluxDBClient(url=self._url, token=self._token,
                                      org=self._org, timeout=30_000)
        self._write_api = self._client.write_api(write_options=write_option)
        self.addNewBucket(self._bucket)

    def disconnect(self):
        with self._update_lock:
            self._write(self._update_queue)
            self._update_queue = []
        self._client.close()

    def getBucketNames(self):
        bucket_names = []
        buckets = self._client.buckets_api().find_buckets().buckets
        for bucket in buckets:
            bucket_names.append(bucket.name)
        return bucket_names

    def addNewBucket(self, bucket_name):
        if bucket_name not in self.getBucketNames():
            retention_rules = BucketRetentionRules(type='expire',
                                                   every_seconds=0)
            self._client.buckets_api().create_bucket(\
                bucket_name=bucket_name,
                retention_rules=retention_rules, org=self._org)

    def query(self):
        """Returns last value for every key/subkey.
        _start and _stop columns do not contain any valuable information, yet
        the influxdb-client module still parses them into datetime object.
        Dropping these columns saves 66% of computation time on the
        influxdb-client module side.
        Parsing of time codes from influxdb can be even faster if ciso8601
        module is installed.
        """

        with self._update_lock:
            self._write(self._update_queue)
            self._update_queue = []
        msg = f'''from(bucket:"{self._bucket}")
            |> range(start: 2007-01-01T00:00:00Z, stop: now())
            |> last(column: "_time")
            |> drop(columns: ["_start", "_stop"])'''
        return self._client.query_api().query(msg)

    def queryHistory(self, measurement, field, fromtime, totime, interval):
        """
        Queries history from InfluxDB.
        """

        with self._update_lock:
            self._write(self._update_queue)
            self._update_queue = []
        t1 = datetime.utcfromtimestamp(fromtime).strftime("%Y-%m-%dT%H:%M:%SZ")
        t2 = datetime.utcfromtimestamp(totime).strftime("%Y-%m-%dT%H:%M:%SZ")
        msg = f'''from(bucket:"{self._bucket}")
            |> range(start: {t1}, stop: {t2})
            |> filter(fn:(r) => r._measurement == "{measurement}")
            |> filter(fn:(r) => r._field == "{field}")'''
        if interval:
            msg += f'|> aggregateWindow(every: {interval}s, fn: last, createEmpty: false)'
        msg += '|> drop(columns: ["_start", "_stop"])'
        yield self._client.query_api().query_stream(msg)

    def update(self, measurement, ts, field, value, expired):
        point = Point(measurement).time(ts).field(f'{field}', value)\
            .tag('expired', expired)
        value_float = self._convert_to_float(value)
        if value_float:
            point_float = Point(measurement).time(ts)\
                .field(f'{field}_float', value_float)\
                .tag('expired', expired)
        with self._update_lock:
            self._update_queue.append(point)
            if value_float:
                self._update_queue.append(point_float)
            if len(self._update_queue) > 100:
                self._write(self._update_queue)
                self._update_queue = []

    def _write(self, points):
        self._write_api.write(bucket=self._bucket, record=points)

    def _convert_to_float(self, value):
        try:
            value = ast.literal_eval(value)
        except Exception:
            value = None
        if value:
            if type(value) in [list, tuple, set]:
                value = list(value)[0] if len(value) == 1 and \
                    type(list(value)[0]) not in [list, tuple, set, dict] \
                    else None
            if isinstance(value, int):
                value = float(value)
        return value if isinstance(value, float) else None


class InfluxDBCacheDatabase(CacheDatabase):
    """Cachedatabase descendant that stores values in InfluxDB.
    In InfluxDB 2.0 a database is called a bucket. Bucket name should be
    passed as a parameter. If a bucket with this name doesn't exist it will be
    created by the InfluxDB_client wrapper.
    This class also requires url of the database, access token and organization
    name, which are set up during installation and initialization of the
    InfluxDB.
    InfluxDB definitions are different to the ones used in NICOS. Nicos
    categories are stored as _measurements, nicos keys are organized in _fields.
    Values are stored as fields' _values. Expired mark is set up
    as _tag. It is better to keep expired as a tag, because then it is
    immideately available in every record obtained from queries. If expired is
    set up as field this field should be requested separately and this comes at
    higher computational cost.
    Values are stored as strings as they are in flatfile database for the sake
    of compatibility. If a value could be converted to float, then it will be
    stored as a float-copy to a special field: {field}_float. This field could
    be accessed through InfluxDB web interface or custom API queries.
    """

    parameters = {
        'url': Param('URL of InfluxDB instance', type=str, mandatory=True),
        'keystoretoken': Param('Id used in the keystore for InfluxDB API token',
                               type=str, default='influxdb', mandatory=True),
        'org': Param('Corresponding organization name created during '
                     'initialization of InfluxDB instance',
                     type=str, mandatory=True),
        'bucket': Param('Name of the bucket where data should be stored',
                        type=str, default='nicos-cache', mandatory=True),
    }

    def doInit(self, mode):
        self._recent = {}
        self._recent_lock = threading.Lock()
        CacheDatabase.doInit(self, mode)
        token = nicoskeystore.getCredential(self.keystoretoken)
        if not token:
            raise ConfigurationError('InfluxDB API token missing in keyring')
        self._client = InfluxDBWrapper(self.url, token, self.org, self.bucket)

    def initDatabase(self):
        tables = self._client.query()
        for table in tables:
            for record in table:
                category = record['_measurement']
                subkey = record['_field']
                time = record['_time'].timestamp()
                with self._recent_lock:
                    if category in self._recent:
                        _, lock, db = self._recent[category]
                        with lock:
                            db[subkey] = CacheEntry(time, None, record['_value'])
                            db[subkey].expired = record['expired'] == 'True'
                    else:
                        db = {}
                        db[subkey] = CacheEntry(time, None, record['_value'])
                        db[subkey].expired = record['expired'] == 'True'
                        self._recent[category] = [None, threading.Lock(), db]

    def doShutdown(self):
        self._client.disconnect()

    def getEntry(self, dbkey):
        category, subkey = dbkey
        with self._recent_lock:
            if category not in self._recent:
                return None
            _, lock, db = self._recent[category]
        with lock:
            return db.get(subkey)

    def iterEntries(self):
        for cat, (_, lock, db) in list(self._recent.items()):
            with lock:
                for subkey, entry in db.items():
                    yield (cat, subkey), entry

    def updateEntries(self, categories, subkey, no_store, entry):
        real_update = True
        for cat in categories:
            with self._recent_lock:
                if cat not in self._recent:
                    self._recent[cat] = [None, threading.Lock(), {}]
                _, lock, db = self._recent[cat]
            update = True
            with lock:
                if subkey in db:
                    curentry = db[subkey]
                    if curentry.value == entry.value and not curentry.expired:
                        curentry.time = entry.time
                        curentry.ttl = entry.ttl
                        update = real_update = False
                    elif entry.value is None and curentry.expired:
                        update = real_update = False
                if update:
                    db[subkey] = entry
                    if not no_store:
                        time = datetime.utcfromtimestamp(entry.time)
                        self._client.update(cat, time, subkey, entry.value,
                                            entry.expired)
        return real_update

    def queryHistory(self, dbkey, fromtime, totime, interval):
        category, subkey = dbkey
        for records in self._client.queryHistory(category, subkey, fromtime,
                                                 totime, interval):
            for record in records:
                time = record['_time'].timestamp()
                entry = CacheEntry(time, None, record['_value'])
                entry.expired = record['expired'] == 'True'
                yield entry

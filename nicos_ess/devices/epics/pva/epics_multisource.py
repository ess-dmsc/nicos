import time

from nicos.core import Param, dictof, pvname, status
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsDeviceBase,
    EpicsRecordComponent,
    RecordType,
    get_from_cache_or,
)


class EpicsMultiSourceComponent(EpicsRecordComponent):
    """Prefix matrix helper for sources sharing one suffix table."""

    def __init__(self, record_fields, sources, **kwargs):
        super().__init__(record_fields, dict.fromkeys(record_fields), **kwargs)
        self.sources = sources

    def source_pv(self, source_id, field):
        return f"{self.sources[source_id]}{self.record_fields[field].pv_suffix}"

    def source_key(self, source_id, field):
        info = self.record_fields[field]
        return f"{source_id}/{info.cache_key or field}"

    def pvs_to_connect(self):
        return [
            self.source_pv(source_id, field)
            for source_id in self.sources
            for field in self.record_fields
        ]

    def subscribe_fields(self, change_callback, connection_callback=None):
        for source_id in self.sources:
            for field, info in self.record_fields.items():
                if not info.monitor:
                    continue
                self.subscriptions.append(
                    self.wrapper.subscribe(
                        self.source_pv(source_id, field),
                        (source_id, field),
                        change_callback,
                        connection_callback,
                        as_string=info.as_string,
                    )
                )

    def get_source_pv(self, source_id, field):
        return self.wrapper.get_pv_value(
            self.source_pv(source_id, field), self.record_fields[field].as_string
        )

    def put_source(self, source_id, field, value):
        self.wrapper.put_pv_value(self.source_pv(source_id, field), value)


class EpicsMultiSourceBase(EpicsDeviceBase):
    """NICOS glue for prefix-matrix devices.

    Multi-source devices should report the worst status across their sources.
    The base class maintains per-source connection state and includes that in
    the default status. Concrete subclasses that add hardware state should merge
    their candidates with ``_source_connection_status(maxage)``.
    """

    _source_connection_cache_key = "_source_connection_status"

    parameters = {
        "sources": Param(
            "Mapping of source id to PV prefix.",
            type=dictof(str, pvname),
            mandatory=True,
            userparam=False,
        ),
    }

    def _create_epics_component(self):
        return EpicsMultiSourceComponent(
            self._record_fields,
            dict(self.sources),
            timeout=self.epicstimeout,
            use_pva=self.pva,
        )

    def _value_change_callback(
        self, name, param, value, units, limits, severity, message, **kwargs
    ):
        source_id, field = param
        ts = time.time()
        self._cache.put(self._name, self._epics.source_key(source_id, field), value, ts)
        if self._record_fields[field].record_type in (
            RecordType.STATUS,
            RecordType.BOTH,
        ):
            self._refresh_status(ts)

    def _connection_change_callback(self, name, param, is_connected, **kwargs):
        source_id, field = param
        ts = time.time()
        if is_connected:
            self.log.debug("%s connected!", name)
            connection_status = status.OK, ""
        else:
            self.log.warning("%s disconnected!", name)
            connection_status = status.UNKNOWN, "lost connection to EPICS"
        self._cache.put(
            self._name,
            self._source_connection_key(source_id, field),
            connection_status,
            ts,
        )
        self._refresh_status(ts)

    def _source_connection_key(self, source_id, field):
        return f"{source_id}/{field}/{self._source_connection_cache_key}"

    def _source_connection_status(self, maxage=0):
        # Connection state is callback-maintained; a fresh status read must not
        # discard a known disconnect just because there is no synchronous read.
        del maxage
        candidates = []
        for source_id in self.sources:
            for field, info in self._record_fields.items():
                if not info.monitor:
                    continue
                if self._cache is None:
                    candidates.append((status.OK, ""))
                    continue
                candidates.append(
                    self._cache.get(
                        self._name,
                        self._source_connection_key(source_id, field),
                        (status.OK, ""),
                    )
                )
        return self._worst_status(candidates)

    @staticmethod
    def _worst_status(candidates):
        candidates = list(candidates)
        if not candidates:
            return status.OK, ""
        return max(candidates, key=lambda candidate: candidate[0])

    def _read_source(self, source_id, field, maxage=None):
        return get_from_cache_or(
            self,
            self._epics.source_key(source_id, field),
            lambda: self._epics.get_source_pv(source_id, field),
            maxage=maxage,
        )

    def _put_source(self, source_id, field, value):
        self._epics.put_source(source_id, field, value)

    def doReadUnit(self):
        return self._config.get("unit", "") or self._params.get("unit", "")

    def _compute_status(self, maxage=0):
        return self._source_connection_status(maxage=maxage)

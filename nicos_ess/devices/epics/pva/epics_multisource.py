import time

from nicos.core import Param, dictof, pvname, status
from nicos_ess.devices.epics.pva.epics_common import (
    EpicsChannelComponent,
    EpicsChannelRole,
    EpicsDeviceBase,
    get_from_cache_or,
)


class EpicsMultiSourceComponent(EpicsChannelComponent):
    """Prefix matrix helper for sources sharing one suffix table."""

    def __init__(self, epics_channels, sources, **kwargs):
        super().__init__(epics_channels, dict.fromkeys(epics_channels), **kwargs)
        self.sources = sources

    def source_pv(self, source_id, channel):
        return f"{self.sources[source_id]}{self.epics_channels[channel].pv_suffix}"

    def source_key(self, source_id, channel):
        info = self.epics_channels[channel]
        return f"{source_id}/{info.cache_key or channel}"

    def pvs_to_connect(self):
        return [
            self.source_pv(source_id, channel)
            for source_id in self.sources
            for channel in self.epics_channels
        ]

    def subscribe_channels(self, change_callback, connection_callback=None):
        for source_id in self.sources:
            for channel, info in self.epics_channels.items():
                if not info.subscribe:
                    continue
                self.subscriptions.append(
                    self.wrapper.subscribe(
                        self.source_pv(source_id, channel),
                        (source_id, channel),
                        change_callback,
                        connection_callback,
                        as_string=info.as_string,
                    )
                )

    def get_source_value(self, source_id, channel):
        return self.wrapper.get_pv_value(
            self.source_pv(source_id, channel),
            self.epics_channels[channel].as_string,
        )

    def put_source_value(self, source_id, channel, value):
        self.wrapper.put_pv_value(self.source_pv(source_id, channel), value)


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
            self._epics_channels,
            dict(self.sources),
            timeout=self.epicstimeout,
            use_pva=self.pva,
        )

    def _value_change_callback(
        self, pv_name, param, value, units, limits, severity, message, **kwargs
    ):
        source_id, channel = param
        ts = time.time()
        self._cache.put(
            self._name, self._epics.source_key(source_id, channel), value, ts
        )
        if self._epics_channels[channel].role in (
            EpicsChannelRole.STATUS,
            EpicsChannelRole.VALUE_AND_STATUS,
        ):
            self._refresh_status(ts)

    def _connection_change_callback(self, pv_name, param, is_connected, **kwargs):
        source_id, channel = param
        ts = time.time()
        if is_connected:
            self.log.debug("%s connected!", pv_name)
            connection_status = status.OK, ""
        else:
            self.log.warning("%s disconnected!", pv_name)
            connection_status = status.UNKNOWN, "lost connection to EPICS"
        self._cache.put(
            self._name,
            self._source_connection_key(source_id, channel),
            connection_status,
            ts,
        )
        self._refresh_status(ts)

    def _source_connection_key(self, source_id, channel):
        return f"{source_id}/{channel}/{self._source_connection_cache_key}"

    def _source_connection_status(self, maxage=0):
        # Connection state is callback-maintained; a fresh status read must not
        # discard a known disconnect just because there is no synchronous read.
        del maxage
        candidates = []
        for source_id in self.sources:
            for channel, info in self._epics_channels.items():
                if not info.subscribe:
                    continue
                if self._cache is None:
                    candidates.append((status.OK, ""))
                    continue
                candidates.append(
                    self._cache.get(
                        self._name,
                        self._source_connection_key(source_id, channel),
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

    def _read_source(self, source_id, channel, maxage=None):
        return get_from_cache_or(
            self,
            self._epics.source_key(source_id, channel),
            lambda: self._epics.get_source_value(source_id, channel),
            maxage=maxage,
        )

    def _put_source(self, source_id, channel, value):
        self._epics.put_source_value(source_id, channel, value)

    def doReadUnit(self):
        return self._config.get("unit", "") or self._params.get("unit", "")

    def _compute_status(self, maxage=0):
        return self._source_connection_status(maxage=maxage)

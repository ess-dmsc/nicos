import time

from nicos.core import CommunicationError, Param, dictof, pvname, status
from nicos_ess.devices.epics.pva.epics_common import (
    LOST_CONNECTION_STATUS,
    EpicsChannelComponent,
    EpicsChannelKind,
    EpicsDeviceBase,
    get_from_cache_or,
    worst_status,
)


class EpicsMultiSourceComponent(EpicsChannelComponent):
    def __init__(self, epics_channels, sources, **kwargs):
        super().__init__(epics_channels, dict.fromkeys(epics_channels), **kwargs)
        self.sources = sources

    def source_pv(self, source_id, channel):
        return f"{self.sources[source_id]}{self.epics_channels[channel].pv_suffix}"

    def source_key(self, source_id, channel):
        cache_key = self.cache_key_for(channel)
        if cache_key is None:
            return None
        return f"{source_id}/{cache_key}"

    def pvs_to_connect(self):
        return [
            self.source_pv(source_id, channel)
            for source_id in self.sources
            for channel, info in self.epics_channels.items()
            if info.kind != EpicsChannelKind.COMMAND and info.connect_on_startup
        ]

    def subscribe_channels(self, change_callback, connection_callback=None):
        for source_id in self.sources:
            for channel, info in self.epics_channels.items():
                if info.kind == EpicsChannelKind.COMMAND or not info.subscribe:
                    continue
                self._subscribe_pv(
                    self.source_pv(source_id, channel),
                    channel,
                    change_callback,
                    connection_callback,
                    info.as_string,
                    source_id=source_id,
                )

    def get_source_value(self, source_id, channel):
        as_string = self.epics_channels[channel].as_string
        return self._on_pv(
            self.source_pv(source_id, channel),
            "reading",
            lambda pv: self.wrapper.get_pv_value(pv, as_string),
        )

    def get_source_alarm(self, source_id, channel):
        return self._on_pv(
            self.source_pv(source_id, channel),
            "reading alarm of",
            lambda pv: self.wrapper.get_alarm_status(pv),
        )

    def put_source_value(self, source_id, channel, value):
        self._on_pv(
            self.source_pv(source_id, channel),
            f"writing {value!r} to",
            lambda pv: self.wrapper.put_pv_value(pv, value),
        )


class EpicsMultiSourceBase(EpicsDeviceBase):
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

    def _on_channel_update(self, update):
        ts = time.time()
        cache_key = self._epics.source_key(update.source_id, update.channel)
        if cache_key is not None:
            self._cache.put(self._name, cache_key, update.value, ts)
        self._cache.put(
            self._name,
            self._source_alarm_key(update.source_id, update.channel),
            (update.severity, update.message),
            ts,
        )
        if self._epics_channels[update.channel].refresh_status_on_update:
            self._refresh_status(ts)

    def _connection_change_affects_status(self, change):
        info = self._epics_channels.get(change.channel)
        return info is not None and info.subscribe

    def _source_alarm_key(self, source_id, channel):
        return f"{source_id}/{channel}/_alarm_status"

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
        # Fold the worst hardware alarm across every subscribed (source,
        # channel); base _status_snapshot adds the connection status on top.
        # Honour maxage like the single-source bases: maxage=0 reads hardware
        # (so a fresh status sees a dead source), otherwise read the cache.
        if getattr(self, "_cache", None) is None:
            return status.OK, ""
        candidates = [
            self._read_source_alarm(source_id, channel, maxage)
            for source_id in self.sources
            for channel, info in self._epics_channels.items()
            if info.subscribe
        ]
        return worst_status(*candidates)

    def _read_source_alarm(self, source_id, channel, maxage):
        def _read():
            try:
                return self._epics.get_source_alarm(source_id, channel)
            except (TimeoutError, CommunicationError):
                return LOST_CONNECTION_STATUS

        return get_from_cache_or(
            self, self._source_alarm_key(source_id, channel), _read, maxage=maxage
        )

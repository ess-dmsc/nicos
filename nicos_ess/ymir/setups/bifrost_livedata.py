description = "The livedata."

devices = dict(
    psc_monitor_counts_total=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="psc_monitor_counts_total",
        source_name="psc_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    overlap_monitor_counts_total=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="overlap_monitor_counts_total",
        source_name="overlap_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    unified_detector_counts_total=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="unified_detector_counts_total",
        source_name="unified_detector",
        workflow_id="bifrost/unified_detector_view/1",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The bifrost livedata collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["bifrost_livedata_nicos_data"],
        commands_topic="bifrost_livedata_commands",
        status_topics=["bifrost_livedata_heartbeat"],
        others=[
            "psc_monitor_counts_total",
            "overlap_monitor_counts_total",
            "unified_detector_counts_total",
        ],
    ),
)

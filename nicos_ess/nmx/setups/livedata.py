description = "The nmx livedata."

devices = dict(
    cbm1_counts_total=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="An nmx livedata channel",
        device_name="monitor1_counts_total",
        workflow_id="nmx/monitor_histogram/1",
        type="counter",
    ),
    cbm2_counts_total=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="An nmx livedata channel",
        device_name="monitor2_counts_total",
        workflow_id="nmx/monitor_histogram/1",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The nmx livedata collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["nmx_livedata_nicos_data"],
        commands_topic="nmx_livedata_commands",
        status_topics=["nmx_livedata_heartbeat"],
        others=["cbm1_counts_total", "cbm2_counts_total"],
    ),
)

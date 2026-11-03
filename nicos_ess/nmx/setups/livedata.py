description = "The nmx livedata."

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated histogram of beam monitor 1",
        device_name="monitor1_histogram",
        source_name="monitor1",
        workflow_id="nmx/monitor_histogram/1",
        type="monitor",
    ),
    monitor_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated histogram of beam monitor 2",
        device_name="monitor2_histogram",
        source_name="monitor2",
        workflow_id="nmx/monitor_histogram/1",
        type="monitor",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The nmx livedata collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["nmx_livedata_nicos_data"],
        commands_topic="nmx_livedata_commands",
        status_topics=["nmx_livedata_heartbeat"],
        others=["monitor_1", "monitor_2"],
    ),
)

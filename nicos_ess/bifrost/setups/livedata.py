description = "The livedata."

excludes = ["just-bin-it"]

devices = dict(
    psc_monitor=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="psc_monitor_histogram",
        source_name="psc_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    overlap_monitor=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="overlap_monitor_histogram",
        source_name="overlap_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    bandwidth_monitor=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="bandwidth_monitor_histogram",
        source_name="bandwidth_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    normalization_monitor=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="normalization_monitor_histogram",
        source_name="normalization_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    elastic_monitor=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="elastic_monitor_histogram",
        source_name="elastic_monitor",
        workflow_id="bifrost/monitor_histogram/1",
        type="counter",
    ),
    detector_image=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="A bifrost livedata channel",
        device_name="unified_detector_image",
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
            "psc_monitor",
            "overlap_monitor",
            "bandwidth_monitor",
            "normalization_monitor",
            "elastic_monitor",
            "detector_image",
        ],
        timers=["timer"],
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
)

startupcode = """
SetDetectors(livedata_collector)
"""

description = "The livedata interface for odin."

excludes = ["just_bin_it"]

devices = dict(
    monitor_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated histogram of beam monitor 1",
        device_name="monitor1_histogram",
        source_name="monitor1",
        workflow_id="odin/monitor_histogram/1",
        type="monitor",
    ),
    monitor_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated histogram of beam monitor 2",
        device_name="monitor2_histogram",
        source_name="monitor2",
        workflow_id="odin/monitor_histogram/1",
        type="monitor",
    ),
    timepix3_image=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Accumulated detector image of the Timepix3",
        device_name="timepix3_image",
        source_name="timepix3",
        workflow_id="odin/odin_detector_xy/1",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The odin livedata collector",
        brokers=configdata("config.KAFKA_BROKERS"),
        data_topics=["odin_livedata_nicos_data"],
        commands_topic="odin_livedata_commands",
        status_topics=["odin_livedata_heartbeat"],
        others=["monitor_1", "monitor_2", "timepix3_image"],
        timers=["timer"],
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
)

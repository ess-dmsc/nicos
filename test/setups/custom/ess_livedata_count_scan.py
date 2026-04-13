# Minimal livedata setup used by command tests.
#
# The collector owns two channels so the tests can exercise both generic
# timer-driven counts and counts where one named channel acts as the soft
# controller.
includes = ["ess_count_scan_common"]

devices = dict(
    channel_1=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 1",
        selector="test/data_reduction/monitor_data/1@monitor/current",
        type="counter",
    ),
    channel_2=device(
        "nicos_ess.devices.datasources.livedata.DataChannel",
        description="Livedata channel 2",
        selector="test/data_reduction/monitor_data/1@monitor/cumulative",
        type="counter",
    ),
    livedata_collector=device(
        "nicos_ess.devices.datasources.livedata.LiveDataCollector",
        description="The livedata detector collector",
        brokers=["localhost:9092"],
        data_topics=["livedata_data"],
        commands_topic="livedata_commands",
        others=["channel_1", "channel_2"],
        timers=["timer"],
    ),
)

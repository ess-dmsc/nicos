description = "The just-bin-it histogrammer."


tof_range = ((0, 0.7143 * 1e9),)  # in ns 0-0.7143 ms
num_bins = (7143,)  # 10us per bin


devices = dict(
    jbi_detector=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="The just-bin-it histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        event_schema="ev44",
        hist_schema="hs01",
        liveinterval=1,
        command_topic="odin_jbi_commands",
        response_topic="odin_jbi_responses",
        statustopic=["odin_jbi_heartbeat"],
        images=[
            "tpx3_det",
        ],
        timers=["timer"],
        # counters=["pulse_counter"],
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
    # Need to define a EVR counter for ODIN
    # pulse_counter=device(
    #     "nicos_ess.devices.epics.pulse_counter.PulseCounter",
    #     description="EVR Pulse Counter",
    #     readpv="ODIN-DtCmn:Ctrl-EVR-001:EvtHCnt-I",
    #     fmtstr="%d",
    # ),
    tpx3_det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="Timepix 3 just-bin-it channel",
        hist_topic="odin_visualisation",
        data_topic="odin_detector_tpx3_empir",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="1-D TOF",
        det_width=4096,
        det_height=4096,
        det_range=(1, 16777216),
        tof_range=(0, 0.7143 * 1e9),  # in ns 0-0.7143 ms
        num_bins=7143,  # 10us per bin
    ),
)

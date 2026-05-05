description = "The just-bin-it histogrammer."

devices = dict(
    det_image1=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="ymir_visualisation",
        data_topic="bifrost_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D DET",
        det_width=900,
        det_height=15,
        det_range=(1, 13500),
    ),
    det_image2=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="A just-bin-it image channel",
        hist_topic="ymir_visualisation",
        data_topic="bifrost_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D TOF",
        det_width=900,
        det_height=15,
        det_range=(1, 13500),
        tof_range=(0, 10000000),
    ),
    ngem_det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItImage",
        description="nGEM just-bin-it channel",
        hist_topic="ymir_visualisation",
        data_topic="ymir_detector",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="evts",
        hist_type="2-D DET",
        det_width=128,
        det_height=128,
        det_range=(1, 16384),
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        fmtstr="%.2f",
        unit="s",
    ),
    pulse_counter=device(
        "nicos_ess.devices.epics.pulse_counter.PulseCounter",
        description="EVR Pulse Counter",
        readpv="YMIR-TS:Ctrl-EVR-01:EvtACnt-I",
        fmtstr="%d",
    ),
    det=device(
        "nicos_ess.devices.datasources.just_bin_it.JustBinItDetector",
        description="The just-bin-it histogrammer",
        brokers=configdata("config.KAFKA_BROKERS"),
        unit="",
        command_topic="ymir_jbi_commands",
        response_topic="ymir_jbi_responses",
        statustopic=["ymir_jbi_heartbeat"],
        images=[
            "det_image1",
            "det_image2",
            "ngem_det",
        ],
        timers=["timer"],
        counters=["pulse_counter"],
        hist_schema="hs01",
    ),
)

startupcode = """
SetDetectors(det)
"""

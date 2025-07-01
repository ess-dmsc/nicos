description = "Fake detector"

devices = dict(
    timer_detector=device(
        "nicos.devices.generic.Detector",
        description="The detector",
        timers=["timer"],
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="The timer",
        fmtstr="%.2f",
        unit="s",
    ),
)
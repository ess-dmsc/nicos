description = "Fake detector"

devices = dict(
    virtual_timer_detector=device(
        "nicos.devices.generic.Detector",
        description="The detector",
        timers=["virtual_timer"],
    ),
    virtual_timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="The timer",
        fmtstr="%.2f",
        unit="s",
    ),
)

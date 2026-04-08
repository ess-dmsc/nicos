includes = ["stdsystem"]

devices = dict(
    axis=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-10, 10),
        curvalue=0,
        unit="deg",
        fmtstr="%.2f",
    ),
    timer=device(
        "nicos_ess.devices.timer.TimerChannel",
        description="Timer",
        unit="s",
        fmtstr="%.2f",
        update_interval=0.01,
    ),
)

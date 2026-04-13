# Shared test setup for command-level ESS count/scan tests.
#
# The custom command-test setups below all reuse the same virtual scan axis and
# timer channel so each test module only needs to declare the detector graph it
# wants to exercise.
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

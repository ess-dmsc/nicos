"""
Virtual detector that can be useful as timer for scans.

Usage in NICOS shell:

AddSetup('virtual_detector') # Can also be added via GUI.
SetDetectors(timer_detector) # Select detector for scans.
scan(virtual_motor_1, 0, 1, 360, timer=1) # Scan from position 0, step size 1, 360 steps.

"""

description = "Virtual detector"

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

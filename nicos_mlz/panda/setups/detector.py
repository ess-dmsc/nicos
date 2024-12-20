description = "detectors"
group = "lowlevel"  # is included by panda.py
display_order = 70

excludes = ["qmesydaq"]

tango_base = "tango://phys.panda.frm2:10000/panda/"

devices = dict(
    timer=device(
        "nicos.devices.entangle.TimerChannel",
        tangodevice=tango_base + "frmctr2/timer",
        visibility=(),
    ),
    mon1=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr2/mon1",
        type="monitor",
        fmtstr="%d",
        visibility=(),
    ),
    mon2=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr2/mon2",
        type="monitor",
        fmtstr="%d",
        visibility=(),
    ),
    det1=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr2/det1",
        type="counter",
        fmtstr="%d",
        visibility=(),
    ),
    det2=device(
        "nicos.devices.entangle.CounterChannel",
        tangodevice=tango_base + "frmctr2/det2",
        type="counter",
        fmtstr="%d",
        visibility=(),
    ),
    mon1_c=device(
        "nicos.devices.tas.OrderCorrectedMonitor",
        description="Monitor corrected for higher-order influence",
        ki="ki",
        mapping={
            1.2: 3.40088101,
            1.3: 2.20258647,
            1.4: 1.97398164,
            1.5: 1.67008065,
            1.6: 1.63189593,
            1.7: 1.51506763,
            1.8: 1.48594030,
            1.9: 1.40500060,
            2.0: 1.35613988,
            2.1: 1.30626513,
            2.2: 1.30626513,
            2.3: 1.25470102,
            2.4: 1.23979656,
            2.5: 1.19249904,
            2.6: 1.18458214,
            2.7: 1.14345899,
            2.8: 1.12199877,
            2.9: 1.10924699,
            3.0: 1.14791169,
            3.1: 1.15693786,
            3.2: 1.06977760,
            3.3: 1.02518334,
            3.4: 1.11537790,
            3.5: 1.11127232,
            3.6: 1.04328656,
            3.7: 1.07179793,
            3.8: 1.10400989,
            3.9: 1.07342487,
            4.0: 1.10219356,
            4.1: 1.00121974,
        },
    ),
    det=device(
        "nicos.devices.generic.Detector",
        description="combined four channel single counter detector",
        timers=["timer"],
        monitors=["mon1", "mon2", "mon1_c"],
        counters=["det1", "det2"],
        # counters = ['det2'],
        postprocess=[("mon1_c", "mon1")],
        maxage=1,
        pollinterval=1,
    ),
)

startupcode = """
SetDetectors(det)
"""

description = "Polarizer setup"
group = "lowlevel"
display_order = 60

excludes = ["virtual_polarizer"]

tango_base = "tango://phys.kws1.frm2:10000/kws1/"

devices = dict(
    polarizer=device(
        "nicos_mlz.kws1.devices.polarizer.Polarizer",
        description="high-level polarizer switcher",
        switcher="pol_switch",
        flipper="flipper",
    ),
    pol_xv=device(
        "nicos.devices.entangle.Motor",
        description="polarizer table front X",
        tangodevice=tango_base + "fzjs7/polarisator_xv",
        unit="mm",
        precision=0.05,
        fmtstr="%.2f",
        visibility=(),
    ),
    pol_yv=device(
        "nicos.devices.entangle.Motor",
        description="polarizer table front Y",
        tangodevice=tango_base + "fzjs7/polarisator_yv",
        unit="mm",
        precision=0.05,
        fmtstr="%.2f",
        visibility=(),
    ),
    pol_xh=device(
        "nicos.devices.entangle.Motor",
        description="polarizer table back X",
        tangodevice=tango_base + "fzjs7/polarisator_xh",
        unit="mm",
        precision=0.05,
        fmtstr="%.2f",
        visibility=(),
    ),
    pol_yh=device(
        "nicos.devices.entangle.Motor",
        description="polarizer table back Y",
        tangodevice=tango_base + "fzjs7/polarisator_yh",
        unit="mm",
        precision=0.05,
        fmtstr="%.2f",
        visibility=(),
    ),
    pol_rot=device(
        "nicos.devices.entangle.Motor",
        description="polarizer rotation",
        tangodevice=tango_base + "fzjs7/polarisator_rot",
        unit="deg",
        precision=0.08,
        fmtstr="%.2f",
        visibility=(),
    ),
    pol_switch=device(
        "nicos_mlz.kws1.devices.polarizer.PolSwitcher",
        description="switch polarizer or neutron guide",
        blockingmove=False,
        moveables=["pol_rot", "pol_xv", "pol_yv", "pol_xh", "pol_yh"],
        readables=[],
        movepos=[5.0, 5.0, 5.0, 5.0],
        mapping={
            "pol": [155.33, 5.0, 5.0, 5.0, 5.0],
            "ng": [335.33, 5.0, 5.0, 5.0, 5.0],
        },
        precision=[0.01, 0.05, 0.05, 0.05, 0.05],
        fallback="unknown",
    ),
    flip_set=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "sps/flipper_write",
        visibility=(),
    ),
    flip_ps=device(
        "nicos.devices.entangle.PowerSupply",
        tangodevice=tango_base + "flipperps/volt",
        visibility=(),
        abslimits=(0, 20),
        timeout=3,
    ),
    flipper=device(
        "nicos_mlz.kws1.devices.flipper.Flipper",
        description="spin flipper after polarizer",
        output="flip_set",
        supply="flip_ps",
    ),
)

extended = dict(
    representative="polarizer",
)

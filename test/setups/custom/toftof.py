# *****************************************************************************
# NICOS, the Networked Instrument Control System of the MLZ
# Copyright (c) 2009-2024 by the NICOS contributors (see AUTHORS)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Jens Krüger <jens.krueger@frm2.tum.de>
#
# *****************************************************************************

name = "test_toftof setup"

includes = ["stdsystem"]

sysconfig = dict(
    datasinks=[
        "tofsink",
        "livesink",
        "nxsink",
    ],
)

devices = dict(
    monitor=device(
        "nicos.devices.generic.VirtualCounter",
        type="monitor",
        presetaliases=["mon1"],
    ),
    timer=device(
        "nicos.devices.generic.VirtualTimer",
        unit="s",
    ),
    image=device(
        "nicos_mlz.toftof.devices.VirtualImage",
        pollinterval=86400,
        datafile="nicos_mlz/toftof/data/test/data.npz",
        background=0,
    ),
    det=device(
        "nicos_mlz.toftof.devices.Detector",
        timers=["timer"],
        monitors=["monitor"],
        images=["image"],
        rc="rc",
        chopper="ch",
        chdelay="chdelay",
        maxage=3,
        pollinterval=None,
        liveinterval=0.1,
        saveintervals=[0.1],
        detinfofile="nicos_mlz/toftof/detinfo.dat",
    ),
    d1=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    d2=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    d3=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    d4=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    d5=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    d6=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    d7=device(
        "nicos_mlz.toftof.devices.Disc",
        speed=0,
        jitter=0,
    ),
    ch=device(
        "nicos_mlz.toftof.devices.VirtualController",
        speed_accuracy=40,
        phase_accuracy=10,
        ch5_90deg_offset=0,
        timeout=600,
        unit="rpm",
        discs=["d1", "d2", "d3", "d4", "d5", "d6", "d7"],
        # abslimits = (0., 27000),
    ),
    chSpeed=device(
        "nicos_mlz.toftof.devices.Speed",
        chopper="ch",
        chdelay="chdelay",
        abslimits=(0, 22000.0),
        unit="rpm",
    ),
    chDS=device(
        "nicos_mlz.toftof.devices.SpeedReadout",
        chopper="ch",
        unit="rpm",
    ),
    chWL=device(
        "nicos_mlz.toftof.devices.Wavelength",
        chopper="ch",
        chdelay="chdelay",
        abslimits=(0.2, 16.0),
        unit="AA",
    ),
    chRatio=device(
        "nicos_mlz.toftof.devices.Ratio",
        chopper="ch",
        chdelay="chdelay",
    ),
    chCRC=device(
        "nicos_mlz.toftof.devices.CRC",
        chopper="ch",
        chdelay="chdelay",
    ),
    chST=device(
        "nicos_mlz.toftof.devices.SlitType",
        chopper="ch",
        chdelay="chdelay",
    ),
    chdelay=device(
        "nicos.devices.generic.ManualMove",
        abslimits=(0, 1000000),
        unit="usec",
    ),
    gx=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-20.0, 20.0),
        unit="mm",
    ),
    gy=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-20.0, 20.0),
        unit="mm",
    ),
    gz=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-14.8, 50.0),
        unit="mm",
    ),
    gcx=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-20.0, 20.0),
        unit="deg",
    ),
    gcy=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-20.0, 20.0),
        unit="deg",
    ),
    gphi=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-20.0, 150.0),
        unit="deg",
    ),
    slit=device(
        "nicos.devices.generic.Slit",
        bottom=device(
            "nicos.devices.generic.VirtualMotor",
            abslimits=(-200, 46.425),
            unit="mm",
        ),
        top=device(
            "nicos.devices.generic.VirtualMotor",
            abslimits=(-200, 46.425),
            unit="mm",
        ),
        left=device(
            "nicos.devices.generic.VirtualMotor",
            abslimits=(-200, 27.5),
            unit="mm",
        ),
        right=device(
            "nicos.devices.generic.VirtualMotor",
            abslimits=(-200, 27.5),
            unit="mm",
        ),
        coordinates="opposite",
        opmode="offcentered",
    ),
    hv0=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(0, 1600),
        ramp=0,
        unit="V",
    ),
    hv1=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(0, 1600),
        ramp=0,
        unit="V",
    ),
    hv2=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(0, 1600),
        ramp=0,
        unit="V",
    ),
    lv0=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv1=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv2=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv3=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv4=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv5=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv6=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    lv7=device("nicos.devices.generic.ManualSwitch", states=["off", "on"]),
    vac0=device(
        "nicos.devices.generic.ManualMove",
        default=1.7e-6,
        abslimits=(0, 1000),
        unit="mbar",
    ),
    vac1=device(
        "nicos.devices.generic.ManualMove",
        default=0.00012,
        abslimits=(0, 1000),
        unit="mbar",
    ),
    vac2=device(
        "nicos.devices.generic.ManualMove",
        default=3.5e-6,
        abslimits=(0, 1000),
        unit="mbar",
    ),
    vac3=device(
        "nicos.devices.generic.ManualMove",
        default=5.0e-6,
        abslimits=(0, 1000),
        unit="mbar",
    ),
    ngc=device(
        "nicos_mlz.toftof.devices.Switcher",
        moveable=device(
            "nicos.devices.generic.VirtualMotor",
            userlimits=(-131.4, 0.0),
            abslimits=(-131.4, 0.0),
            unit="mm",
        ),
        mapping={
            "linear": -5.1,
            "focus": -131.25,
        },
    ),
    rc=device(
        "nicos.devices.generic.ManualSwitch",
        states=["off", "on"],
    ),
    B=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(0, 1),
        unit="T",
    ),
    P=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(0, 1000),
        unit="mbar",
    ),
    T=device(
        "nicos.devices.generic.VirtualMotor",
        abslimits=(-40, 100),
        unit="degC",
    ),
    tofsink=device(
        "nicos_mlz.toftof.datasinks.TofImageSink",
        filenametemplate=["%(pointcounter)08d_0000.raw"],
    ),
    nxsink=device(
        "nicos_mlz.toftof.datasinks.NexusSink",
        templateclass="nicos_mlz.toftof.datasinks.nexustemplate.LegacyTemplate",
        filenametemplate=["TOFTOF%(pointcounter)08d.nxs"],
    ),
    livesink=device("nicos_mlz.toftof.datasinks.LiveViewSink"),
)

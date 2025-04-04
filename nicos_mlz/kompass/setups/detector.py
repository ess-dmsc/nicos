description = "qmesydaq detector devices"

# included by kompass
group = "lowlevel"

tango_base = "tango://kompasshw.kompass.frm2.tum.de:10000/kompass/qmesydaq/"

sysconfig = dict(
    datasinks=[
        "LivePNGSink",
        "LivePNGSinkLog",
    ],  #'Histogram', 'Listmode'],
)

devices = dict(
    LiveViewSink=device(
        "nicos.devices.datasinks.LiveViewSink",
        description="Sends image data to LiveViewWidget",
        filenametemplate=[],
    ),
    LivePNGSinkLog=device(
        "nicos.devices.datasinks.PNGLiveFileSink",
        description="Saves live image as .png every now and then",
        filename="/control/webroot/live_log.png",
        log10=True,
        interval=15,
    ),
    LivePNGSink=device(
        "nicos.devices.datasinks.PNGLiveFileSink",
        description="Saves live image as .png every now and then",
        filename="/control/webroot/live_lin.png",
        log10=False,
        interval=15,
    ),
    Histogram=device(
        "nicos_mlz.devices.qmesydaqsinks.HistogramSink",
        description="Histogram data written via QMesyDAQ",
        image="det1_image",
        subdir="mtxt",
        filenametemplate=["%(pointcounter)07d.mtxt"],
        detectors=["det"],
    ),
    Listmode=device(
        "nicos_mlz.devices.qmesydaqsinks.ListmodeSink",
        description="Listmode data written via QMesyDAQ",
        image="det1_image",
        subdir="list",
        filenametemplate=["%(pointcounter)07d.mdat"],
        detectors=["det"],
    ),
    det1_mon1=device(
        "nicos.devices.entangle.CounterChannel",
        description="QMesyDAQ Counter0",
        tangodevice=tango_base + "counter0",
        type="monitor",
    ),
    det1_mon2=device(
        "nicos.devices.entangle.CounterChannel",
        description="QMesyDAQ Counter1",
        tangodevice=tango_base + "counter1",
        type="monitor",
    ),
    det1_mon3=device(
        "nicos.devices.entangle.CounterChannel",
        description="QMesyDAQ Counter2 (reference for tisane)",
        tangodevice=tango_base + "counter2",
        type="monitor",
    ),
    det1_mon4=device(
        "nicos.devices.entangle.CounterChannel",
        description="QMesyDAQ Counter2 (reference for tisane)",
        tangodevice=tango_base + "counter3",
        type="monitor",
    ),
    det1_ev=device(
        "nicos.devices.entangle.CounterChannel",
        description="QMesyDAQ Events channel",
        tangodevice=tango_base + "events",
        type="counter",
    ),
    det1_timer=device(
        "nicos.devices.entangle.TimerChannel",
        description="QMesyDAQ Timer",
        tangodevice=tango_base + "timer",
    ),
    det1_image=device(
        "nicos.devices.vendor.qmesydaq.tango.ImageChannel",
        description="QMesyDAQ Image",
        tangodevice=tango_base + "det",
    ),
    det1_raw=device(
        "nicos.devices.vendor.qmesydaq.tango.ImageChannel",
        description="QMesyDAQ RAW Image",
        tangodevice=tango_base + "detraw",
    ),
    det1_amp=device(
        "nicos.devices.vendor.qmesydaq.tango.ImageChannel",
        description="QMesyDAQ Amplitudes",
        tangodevice=tango_base + "detamp",
    ),
    det1=device(
        "nicos.devices.generic.Detector",
        description="QMesyDAQ Image type Detector1",
        timers=["det1_timer"],
        monitors=["det1_mon1", "det1_mon2", "det1_mon3", "det1_mon4"],
        images=["det1_image"],
        liveinterval=30.0,
    ),
)

startupcode = """
SetDetectors(det1)
"""

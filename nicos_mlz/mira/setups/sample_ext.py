description = "sample table (external control)"
group = "lowlevel"

tango_base = "tango://miractrl.mira.frm2.tum.de:10000/mira/"

devices = dict(
    co_stt=device(
        "nicos.devices.entangle.Sensor",
        visibility=(),
        tangodevice=tango_base + "sample/phi_ext_enc",
        unit="deg",
    ),
    mo_stt=device(
        "nicos.devices.entangle.Motor",
        visibility=(),
        tangodevice=tango_base + "sample/phi_ext_mot",
        unit="deg",
        precision=0.002,
    ),
    stt=device(
        "nicos_mlz.mira.devices.axis.HoveringAxis",
        description="sample two-theta angle",
        abslimits=(-120, 120),
        motor="mo_stt",
        coder="co_stt",
        startdelay=1,
        stopdelay=2,
        switch="air_sample_ana",
        switchvalues=(0, 1),
        fmtstr="%.3f",
        precision=0.002,
    ),
    air_mono=device(
        "nicos.devices.generic.ManualMove",
        abslimits=(0, 1),
        unit="",
        visibility=(),
    ),
    air_sample_ana=device(
        "nicos_mlz.mira.devices.refcountio.MultiDigitalOutput",
        outputs=["air_sample", "air_ana"],
        unit="",
        visibility=(),
    ),
    air_sample=device(
        "nicos_mlz.mira.devices.refcountio.RefcountDigitalOutput",
        tangodevice=tango_base + "air/sample_ext",
        visibility=(),
    ),
    air_ana=device(
        "nicos.devices.entangle.DigitalOutput",
        tangodevice=tango_base + "air/det_ext",
        visibility=(),
    ),
)

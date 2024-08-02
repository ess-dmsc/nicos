description = "Installs the Kappa goniometer into NICOS"

excludes = ["zebratas", "zebranb", "zebraeuler"]

includes = ["monochromator", "sample"]

sysconfig = dict(
    instrument="ZEBRA",
)

devices = dict(
    ZEBRA=device(
        "nicos_sinq.sxtal.instrument.KappaSXTal",
        description="instrument object",
        instrument="SINQ ZEBRA",
        responsible="Oksana Zaharko <oksana.zaharko@psi.ch>",
        operators=["Paul-Scherrer-Institut (PSI)"],
        facility="SINQ, PSI",
        website="https://www.psi.ch/sinq/zebra/",
        stt="stt",
        omega="som",
        kappa="sch",
        kphi="sph",
        mono="wavelength",
        center_counter="counts",
        center_steps=[0.1, 0.1, 0.2, 0.2],
        kappa_angle=54.0,
        right_hand=True,
    ),
    h=device(
        "nicos.core.device.DeviceAlias",
        description="Alias for the h of hkl",
        alias="ZEBRA.h",
        devclass="nicos.devices.sxtal.instrument.SXTalIndex",
    ),
    k=device(
        "nicos.core.device.DeviceAlias",
        description="Alias for the k of hkl",
        alias="ZEBRA.k",
        devclass="nicos.devices.sxtal.instrument.SXTalIndex",
    ),
    l=device(
        "nicos.core.device.DeviceAlias",
        description="Alias for the l of hkl",
        alias="ZEBRA.l",
        devclass="nicos.devices.sxtal.instrument.SXTalIndex",
    ),
)

startupcode = """
maw(zebramode, 'kappa')
ublist.column_headers=(('H', 'K', 'L'), ('STT', 'OM', 'PHI'),())
messlist.column_headers=(('H', 'K', 'L'), ('STT', 'OM', 'PHI'),())
satref.column_headers=(('H', 'K', 'L'), ('STT', 'OM', 'PHI'),())
"""

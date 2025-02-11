description = "Optical bank devices for polarization analysis"

group = "lowlevel"

devices = dict(
    polcol=device(
        "nicos_mlz.puma.devices.Collimator",
        description="polarisation collimator",
        # motor = device('nicos_mlz.puma.devices.VirtualReferenceMotor',
        #     abslimits = (-250000, 250000),
        #     unit = 'steps',
        #     fmtstr = '%d',
        #     refswitch = 'low',
        #     refpos = -250000,
        # ),
        motor=device(
            "nicos.devices.generic.VirtualMotor",
            curvalue=-0.6,
            fmtstr="%.2f",
            abslimits=(-5, 5),
            unit="deg",
        ),
        precision=0,
        backlash=-200,
    ),
    def1=device(
        "nicos_mlz.puma.devices.Deflector",
        description="First deflector",
        motor=device(
            "nicos_mlz.puma.devices.VirtualReferenceMotor",
            curvalue=-0.8,
            refswitch="low",
            # refpos = -5.5,
            refpos=(497171 - 500000) / 577.35,
            abslimits=(-5.5, 5.5),
            fmtstr="%6.3f",
            unit="deg",
        ),
        precision=0,
        backlash=-1,
    ),
    def2=device(
        "nicos_mlz.puma.devices.Deflector",
        description="Second deflector",
        motor=device(
            "nicos_mlz.puma.devices.VirtualReferenceMotor",
            refswitch="low",
            # refpos = -5.5,
            refpos=(497171 - 500000) / 577.35,
            abslimits=(-5.5, 5.5),
            unit="deg",
            curvalue=0.75,
            fmtstr="%6.3f",
        ),
        precision=0,
        backlash=-1,
    ),
)

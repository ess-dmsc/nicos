description = "Virtual sample aperture and table"
group = "lowlevel"

devices = dict(
    ap_sam_x0=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample aperture horz. blade 0",
        visibility=(),
    ),
    ap_sam_y0=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample aperture vert. blade 0",
        visibility=(),
    ),
    ap_sam_x1=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample aperture horz. blade 1",
        visibility=(),
    ),
    ap_sam_y1=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample aperture vert. blade 1",
        visibility=(),
    ),
    ap_sam=device(
        "nicos.devices.generic.Slit",
        description="sample aperture",
        coordinates="opposite",
        opmode="offcentered",
        left="ap_sam_x1",
        right="ap_sam_x0",
        bottom="ap_sam_y0",
        top="ap_sam_y1",
    ),
    sam_trans_x=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample translation left-right",
        fmtstr="%.1f",
    ),
    sam_trans_y=device(
        "nicos_mlz.kws1.devices.virtual.Standin",
        description="sample translation up-down",
        fmtstr="%.1f",
    ),
)

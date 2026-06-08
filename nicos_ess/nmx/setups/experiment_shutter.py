description = "NMX experiment shutter"

pv_root = "NMX-ExSht:MC-Pne-01:"

# TODO: Use mapped or epics shutter?  
devices = dict(
    experiment_shutter_status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Experiment shutter status",
        readpv=f"{pv_root}ShtAuxBits07",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),
    experiment_shutter=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Experiment shutter control",
        readpv=f"{pv_root}ShtOpen",
        writepv=f"{pv_root}ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
    ),

    experiment_shutter__epics_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Experiment Shutter",
        writepv=f"{pv_root}ShtOpen",
        readpv=f"{pv_root}ShtAuxBits07",
        resetpv=f"{pv_root}ShtErrRst",
        msgtxt=f"{pv_root}ShtMsgTxt",
    ),
)
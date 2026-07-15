description = "NMX shutters"

pv_root = "NMX-ExSht:MC-Pne-01:"

# TODO: Mapped devices added just for redundance.
# They will probably be removed after user tests.
devices = dict(
    experiment_shutter=device(
        "nicos_ess.devices.epics.pva.shutter.EpicsShutter",
        description="Experiment Shutter",
        writepv=f"{pv_root}ShtOpen",
        readpv=f"{pv_root}ShtAuxBits07",
        statuspv=f"{pv_root}ShtStatusCode",
        resetpv=f"{pv_root}ShtErrRst",
        msgtxt=f"{pv_root}ShtMsgTxt",
    ),
    experiment_shutter__control=device(
        "nicos_ess.devices.epics.pva.EpicsMappedMoveable",
        description="Experiment shutter control",
        readpv=f"{pv_root}ShtOpen",
        writepv=f"{pv_root}ShtOpen",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility={},
    ),
    experiment_shutter__status=device(
        "nicos_ess.devices.epics.pva.EpicsMappedReadable",
        description="Experiment shutter status",
        readpv=f"{pv_root}ShtAuxBits07",
        pva=True,
        monitor=True,
        pollinterval=0.5,
        maxage=None,
        visibility={},
    ),
)

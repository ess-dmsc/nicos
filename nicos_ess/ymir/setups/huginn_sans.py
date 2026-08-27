description = "The Huginn SANS system."

pv_root = "SES-HGNSANS-01:"
pv_root_ls_1 = f"{pv_root}Tctrl-LS336-001:"
pv_root_ls_2 = f"{pv_root}Tctrl-LS336-002:"
pv_root_ls_3 = f"{pv_root}Tctrl-LS336-003:"

devices = dict(
    T_cuvette_1=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The cuvette temperature",
        readpv=f"{pv_root_ls_1}KRDG0",
    ),
    T_cuvette_1_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the cuvette",
        readpv=f"{pv_root_ls_1}SETP3",
        writepv=f"{pv_root_ls_1}SETP_S3",
        abslimits=(0.0, 400),
    ),
    T_cuvette_2=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The cuvette temperature",
        readpv=f"{pv_root_ls_1}KRDG1",
    ),
    T_cuvette_2_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the cuvette",
        readpv=f"{pv_root_ls_1}SETP4",
        writepv=f"{pv_root_ls_1}SETP_S4",
        abslimits=(0.0, 400),
    ),
    T_cuvette_3=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The cuvette temperature",
        readpv=f"{pv_root_ls_2}KRDG0",
    ),
    T_cuvette_3_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the cuvette",
        readpv=f"{pv_root_ls_2}SETP3",
        writepv=f"{pv_root_ls_2}SETP_S3",
        abslimits=(0.0, 400),
    ),
    T_cuvette_4=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The cuvette temperature",
        readpv=f"{pv_root_ls_2}KRDG1",
    ),
    T_cuvette_4_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the cuvette",
        readpv=f"{pv_root_ls_2}SETP4",
        writepv=f"{pv_root_ls_2}SETP_S4",
        abslimits=(0.0, 400),
    ),
    T_cuvette_5=device(
        "nicos_ess.devices.epics.pva.EpicsReadable",
        description="The cuvette temperature",
        readpv=f"{pv_root_ls_3}KRDG0",
    ),
    T_cuvette_5_setpoint=device(
        "nicos_ess.devices.epics.pva.EpicsAnalogMoveable",
        description="The setpoint for the cuvette",
        readpv=f"{pv_root_ls_3}SETP3",
        writepv=f"{pv_root_ls_3}SETP_S3",
        abslimits=(0.0, 400),
    ),
)

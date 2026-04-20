description = "Temperature Readouts for Both Selene Guide 1 and 2"

sg1_rb_root = "ESTIA-SG1Rb:MC-"
sg2_rb_root = "ESTIA-SG2Rb:MC-"
sg1_pt_root = "ESTIA-SG1Tp:MC-Temp-"
sg2_pt_root = "ESTIA-SG2Tp:MC-Temp-"

devices = dict(
    # Selene Guide 1 PT-100 Temperatures
    sg1_pt100_01=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 01",
        readpv=f"{sg1_pt_root}01:Temp",
        visibility=(),
    ),
    sg1_pt100_02=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 02",
        readpv=f"{sg1_pt_root}02:Temp",
        visibility=(),
    ),
    sg1_pt100_03=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 03",
        readpv=f"{sg1_pt_root}03:Temp",
        visibility=(),
    ),
    sg1_pt100_04=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 04",
        readpv=f"{sg1_pt_root}04:Temp",
        visibility=(),
    ),
    sg1_pt100_05=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 05",
        readpv=f"{sg1_pt_root}05:Temp",
        visibility=(),
    ),
    sg1_pt100_06=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 06",
        readpv=f"{sg1_pt_root}06:Temp",
        visibility=(),
    ),
    sg1_pt100_07=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 07",
        readpv=f"{sg1_pt_root}07:Temp",
        visibility=(),
    ),
    sg1_pt100_08=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Top in Air",
        readpv=f"{sg1_pt_root}08:Temp",
        visibility=(),
    ),
    sg1_pt100_09=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="upstream Foot in Air",
        readpv=f"{sg1_pt_root}09:Temp",
        visibility=(),
    ),
    sg1_pt100_10=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Downstream Foot in Air",
        readpv=f"{sg1_pt_root}10:Temp",
        visibility=(),
    ),
    sg1_pt100_11=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Reference in Vaccum Base Plate",
        readpv=f"{sg1_pt_root}11:Temp",
        visibility=(),
    ),
    sg1_pt100_12=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Reference in Air",
        readpv=f"{sg1_pt_root}12:Temp",
        visibility=(),
    ),
    # Selene Guide 1 Cart, Robot, Driver Temperatures
    sg1_robot_x_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot LinX Temp",
        readpv=f"{sg1_rb_root}LinX-01:Mtr-Temp",
        visibility=(),
    ),
    sg1_robot_z_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot LinZ Temp",
        readpv=f"{sg1_rb_root}LinZ-01:Mtr-Temp",
        visibility=(),
    ),
    sg1_driver_approach_temp_01=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 1 Approach Temp",
        readpv=f"{sg1_rb_root}LinY-01:Mtr-Temp",
        visibility=(),
    ),
    sg1_driver_adjust_temp_01=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 1 Adjust Temp",
        readpv=f"{sg1_rb_root}RotY-01:Mtr-Temp",
        visibility=(),
    ),
    sg1_driver_approach_temp_02=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 2 Approach Temp",
        readpv=f"{sg1_rb_root}LinY-02:Mtr-Temp",
        visibility=(),
    ),
    sg1_driver_adjust_temp_02=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 2 Adjust Temp",
        readpv=f"{sg1_rb_root}RotY-02:Mtr-Temp",
        visibility=(),
    ),
    sg1_cart_x_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Metrology Cart LinY Temp",
        readpv="ESTIA-SG1Ct:MC-LinX-01:Mtr-Temp",
        visibility=(),
    ),
    sg1_cart_approach_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Metrology Cart RotZ Temp",
        readpv="ESTIA-SG1Ct:MC-RotZ-01:Mtr-Temp",
        visibility=(),
    ),
    # Selene Guide 2 PT-100 Temperatures
    sg2_pt100_01=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 01",
        readpv=f"{sg2_pt_root}01:Temp",
        visibility=(),
    ),
    sg2_pt100_02=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 02",
        readpv=f"{sg2_pt_root}02:Temp",
        visibility=(),
    ),
    sg2_pt100_03=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 03",
        readpv=f"{sg2_pt_root}03:Temp",
        visibility=(),
    ),
    sg2_pt100_04=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 04",
        readpv=f"{sg2_pt_root}04:Temp",
        visibility=(),
    ),
    sg2_pt100_05=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 05",
        readpv=f"{sg2_pt_root}05:Temp",
        visibility=(),
    ),
    sg2_pt100_06=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 06",
        readpv=f"{sg2_pt_root}06:Temp",
        visibility=(),
    ),
    sg2_pt100_07=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Pt100 Sensor 07",
        readpv=f"{sg2_pt_root}07:Temp",
        visibility=(),
    ),
    sg2_pt100_08=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Vaccum Vessel Top in Air",
        readpv=f"{sg2_pt_root}08:Temp",
        visibility=(),
    ),
    sg2_pt100_09=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="upstream Foot in Air",
        readpv=f"{sg2_pt_root}09:Temp",
        visibility=(),
    ),
    sg2_pt100_10=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Downstream Foot in Air",
        readpv=f"{sg2_pt_root}10:Temp",
        visibility=(),
    ),
    sg2_pt100_11=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Reference in Vaccum Base Plate",
        readpv=f"{sg2_pt_root}11:Temp",
        visibility=(),
    ),
    sg2_pt100_12=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Reference in Air",
        readpv=f"{sg2_pt_root}12:Temp",
        visibility=(),
    ),
    # Selene Guide 2 Cart, Robot, Driver Temperatures
    sg2_robot_x_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot LinX Temp",
        readpv=f"{sg2_rb_root}LinX-01:Mtr-Temp",
        visibility=(),
    ),
    sg2_robot_z_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot LinZ Temp",
        readpv=f"{sg2_rb_root}LinZ-01:Mtr-Temp",
        visibility=(),
    ),
    sg2_driver_approach_temp_01=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 1 Approach Temp",
        readpv=f"{sg2_rb_root}LinY-01:Mtr-Temp",
        visibility=(),
    ),
    sg2_driver_adjust_temp_01=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 1 Adjust Temp",
        readpv=f"{sg2_rb_root}RotY-01:Mtr-Temp",
        visibility=(),
    ),
    sg2_driver_approach_temp_02=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 2 Approach Temp",
        readpv=f"{sg2_rb_root}LinY-02:Mtr-Temp",
        visibility=(),
    ),
    sg2_driver_adjust_temp_02=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Robot Driver 2 Adjust Temp",
        readpv=f"{sg2_rb_root}RotY-02:Mtr-Temp",
        visibility=(),
    ),
    sg2_cart_x_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Metrology Cart LinY Temp",
        readpv="ESTIA-SG2Ct:MC-LinX-01:Mtr-Temp",
        visibility=(),
    ),
    sg2_cart_approach_temp=device(
        "nicos_ess.devices.epics.pva.EpicsStringReadable",
        description="Metrology Cart RotZ Temp",
        readpv="ESTIA-SG2Ct:MC-RotZ-01:Mtr-Temp",
        visibility=(),
    ),
)

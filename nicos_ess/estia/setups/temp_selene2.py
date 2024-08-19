description = "Temperature measurement and control"

devices = dict(
    SG2T01=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp1",
        statuspv=None,
        unit="°C",
        description="Reference Air",
    ),
    SG2T02=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp2",
        statuspv=None,
        unit="°C",
        description="Reference Vacuum",
    ),
    SG2T03=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp3",
        statuspv=None,
        unit="°C",
        description="Upstream Carrier",
    ),
    SG2T04=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp4",
        statuspv=None,
        unit="°C",
        description="Upstream Foot in Vacuum",
    ),
    SG2T05=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp5",
        statuspv=None,
        unit="°C",
        description="Upstream Foot in Air",
    ),
    SG2T06=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp6",
        statuspv=None,
        unit="°C",
        description="Downstream Foot in Vacuum",
    ),
    SG2T07=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp7",
        statuspv=None,
        unit="°C",
        description="Downstream Foot in Air",
    ),
    SG2T08=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp8",
        statuspv=None,
        unit="°C",
        description="Downstream Carrier",
    ),
    SG2T09=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp9",
        statuspv=None,
        unit="°C",
        description="Center Carrier",
    ),
    SG2T10=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp10",
        statuspv=None,
        unit="°C",
        description="Vacuum Vessel Top",
    ),
    SG2T11=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp11",
        statuspv=None,
        unit="°C",
        description="Metrology Rack Carrier Side",
    ),
    SG2T12=device(
        "nicos_ess.estia.devices.pt100.EpicsPT100Temperature",
        readpv="ESTIA-Sel2:MC-MCU-01:Temp12",
        statuspv=None,
        unit="°C",
        description="Metrology Rack Vessel Side",
    ),
    # julabo=device(
    #     'nicos_ess.estia.devices.julabo.TemperatureController',
    #     description='The Julabo',
    #     pvprefix='ESTIA-JUL25HL-001',
    #     readpv='ESTIA-JUL25HL-001:TEMP',
    #     writepv='ESTIA-JUL25HL-001:TEMP:SP1',
    #     targetpv='ESTIA-JUL25HL-001:TEMP:SP1:RBV',
    #     statuscodepv='ESTIA-JUL25HL-001:STATUS',
    #     statusmsgpv='ESTIA-JUL25HL-001:STATUSc',
    #     switchpvs={
    #         'read': 'ESTIA-JUL25HL-001:MODE:SP',
    #         'write': 'ESTIA-JUL25HL-001:MODE:SP'
    #     },
    #     switchstates={
    #         'enable': 1,
    #         'disable': 0
    #     },
    #     precision=0.5,
    # ),
)

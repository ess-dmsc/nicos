description = "Sample Environment Flow-Cryo"

pv_root = "ESTIA-SES:Cryo-TC-001:"
devices = dict(
    cryostat=device(
        "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInput",
        description="Input A of the Flow Cryo",
        pvroot=pv_root,
        input_pos="A",
        ramp="Off",
    ),
    transport_holder=device(
        "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInput",
        description="Input A of the Flow Cryo",
        pvroot=pv_root,
        input_pos="B",
        ramp="Off",
    ),
    double_sample_holder=device(
        "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInput",
        description="Input A of the Flow Cryo",
        pvroot=pv_root,
        input_pos="C",
        ramp="Off",
    ),
)

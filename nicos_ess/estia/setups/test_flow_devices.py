description = "Sample Environment Flow-Cryo. Each Device controls one Input"

pv_root = "ESTIA-SES:Cryo-TC-001:"
devices = dict(
    cryostat=device(
        "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInput",
        description="Input A of the Flow Cryo",
        pvroot=pv_root,
        input_pos="A",
        output_num=1,
        ramp="Off",
    ),
    transport_holder=device(
        "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInput",
        description="Input A of the Flow Cryo",
        pvroot=pv_root,
        input_pos="B",
        output_num=2,
        ramp="Off",
    ),
    # double_sample_holder=device(
    #     "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInput",
    #     description="Input A of the Flow Cryo",
    #     pvroot=pv_root,
    #     input_pos="C",
    #     output_num=3,
    #     ramp="Off",
    # ),
)

description = "Sample Environment Flow-Cryo"

pv_root = "ESTIA-SES:Cryo-TC-001:"
devices = dict(
    # flow_input_changer=device(
    #     "nicos_ess.devices.mapped_controller.MappedController",
    #     description="Mapping to each flow cryo input",
    #     controlled_device="fake_input_a",
    #     #controlled_device="flow_cryo_controller",
    #     mapping={
    #         "A:Cryostat":10,
    #         "B:Transport Holder":20,
    #         "C:Double Sample Holder":30,
    #         "D:Not Configured": 0
    #     },
    # ),
    # fake_input_a=device(
    #     "nicos.devices.generic.VirtualMotor",
    #     description="Fake A input",
    #     fmtstr="%.2f",
    #     unit="mm",
    #     speed=5,
    #     abslimits=(0,100),
    # ),
    # fake_input_b=device(
    #     "nicos.devices.generic.VirtualMotor",
    #     description="Fake B input",
    #     fmtstr="%.2f",
    #     unit="mm",
    #     speed=5,
    #     abslimits=(0,100),
    # ),
    # fake_input_c=device(
    #     "nicos.devices.generic.VirtualMotor",
    #     description="Fake C input",
    #     fmtstr="%.2f",
    #     unit="mm",
    #     speed=5,
    #     abslimits=(0,100),
    # ),
    cryostat_fc=device(
        "nicos_ess.estia.devices.flow_cryo_control.FlowCryoInputController",
        description="Input A of the Flow Cryo",
        pvroot=pv_root,
        input_pos="A",
    ),
)

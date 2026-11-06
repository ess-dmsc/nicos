from nicos_ess.freia.devices import collimation_helpers as ch


class TestCollimationSlitHelpers:
    def test_res_to_slits_with_known_solution(self):
        slits = ch.resolution_to_slit(
            l2=0.5,
            l12=17.6,
            ia=0.24,
            res=0.072,
            footprint=90,
        )
        assert round_results(slits) == [10.5407, 0.0754]

    def test_slits_to_res_with_known_solution(self):
        res_info = ch.slit_to_resolution(
            l2=0.5,
            l12=17.6,
            ia=0.24,
            slit1=10,
            slit2=0.4,
        )
        assert round_results(res_info) == [166.028, 95.4932, 7.0535, 9.2281]


def round_results(list, rounding=4):
    for i, val in enumerate(list):
        list[i] = round(val, rounding)
    return list

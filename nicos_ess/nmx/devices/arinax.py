from nicos_ess.devices.mapped_controller import MappedController

class StringEpicsMappedMoveable(EpicsMappedMoveable):
    """
    An EpicsMappedMoveable that writes the ENUM string instead of its index.
    """

    #valuetype = str
    #
    #parameters = {
    #    "readpv": Param(
    #        "PV for reading device value", type=pvname, mandatory=True, userparam=False
    #    ),
    #    "writepv": Param(
    #        "PV for writing device target", type=pvname, mandatory=True, userparam=False
    #    ),
    #    "targetpv": Param(
    #        "Optional target readback PV.",
    #        type=none_or(pvname),
    #        mandatory=False,
    #        userparam=False,
    #    ),
    #}

    def doStart(self, value):
        self._epics_wrapper.put_pv_value(self.writepv, value)


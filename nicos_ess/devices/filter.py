from nicos.core import Moveable, Param, Override, status, tupleof

class FilterMenu(Moveable):
    '''Lets the user choose a filter'''

    parameters = {
        "curstatus" : Param(
                    "Current status",
                    type=tupleof(int, str),
                    settable=True,
                    default=(status.OK, "idle"),
                ),
        "curvalue": Param("Current value", type=str),
    }

    parameter_overrides = {
        "maxage": Override(default=0),
        "pollinterval": Override(default=None, userparam=False, settable=False),
        "unit": Override(mandatory=False),
    }

    hardware_access = False

    def doStart(self, target):
        self._setROParam("curvalue", target)

    def doStatus(self, maxage=0):
        return self.curstatus

    def doRead(self, maxage=0):
        return self.curvalue
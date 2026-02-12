from nicos.core import SIMULATION, Moveable, Override, Param, pvname, status, usermethod
from nicos.devices.abstract import CanReference
from nicos_ess.devices.epics.pva.epics_devices import (
    EpicsParameters,
    create_wrapper,
    get_from_cache_or,
)


class CetoniPumpController(EpicsParameters, CanReference, Moveable):
    """
    A device for controlling a Cetoni syringe pump

     The device:
      - exposes the mapped commands: start / stop / purge / pause / resume
      - reads the current textual *state* from the attached `status` device
      - reads error text from `message_pv` (non-empty => ERROR)
      - writes to start/stop/purge/pause PVs as before
    """

    parameters = {
        "pvroot": Param(
            "The root of the PV.",
            type=pvname,
            mandatory=True,
            settable=False,
            userparam=False,
        ),
        "innerdiameter": Param(
            "The inner diameter of the syringe",
            type=float,
        ),
        "maxstroke": Param(
            "The maximum stroke length of the piston",
            type=float,
        ),
        "maxpressure": Param(
            "The maximum allowed pressure",
            type=float,
        ),
        "stepsize": Param(
            "Define step size for quick aspiration/dispensing of defined volume",
            type=float,
        ),
    }

    parameter_overrides = {
        # readpv and writepv are determined automatically from the base PV
        "readpv": Override(mandatory=False, userparam=False, settable=False),
        "writepv": Override(mandatory=False, userparam=False, settable=False),
        "unit": Override(mandatory=False, settable=False, default=""),
    }

    def doPreinit(self, mode):
        self._record_fields = {
            "readpv": "FilledVolume",
            "writepv": "C_SetFillVol",
            "pressure": "Pressure",
            "ispumping": "IsPumping",
            "isfault": "FaultState",
            "ishomed": "RefPosInitd",
            "flowrate_rb": "FlowRate-RB",
            "flowrate_sp": "FlowRate-RB",
            "aspiratestep": "C_AspirateStep",
            "dispensestep": "C_DispenseStep",
            "innerdiameter_rb": "SyrInnerDiam-RB",
            "innerdiameter_sp": "SyrInnerDiam-SP",
            "maxstroke_rb": "SyrMaxPstStrk-RB",
            "maxstroke_sp": "SyrMaxPstStrk-SP",
            "maxpressure_rb": "MaxPressure-RB",
            "maxpressure_sp": "MaxPressure-SP",
            "stepsize_rb": "StepSize-RB",
            "stepsize_sp": "StepSize-SP",
            "home": " InitPosition",
        }
        self._epics_subscriptions = []
        self._epics_wrapper = create_wrapper(self.epicstimeout, self.pva)

    def _get_pv_name(self, pvparam):
        return f"{self.pvroot}{self._record_fields[pvparam]}"

    def _read_pv(self, name, as_string=False):
        return self._epics_wrapper.get_pv_value(name, as_string=as_string)

    def _set_pv(self, name, value):
        self._epics_wrapper.put_pv_value(name, value)

    def doRead(self, maxage=0):
        return self._epics_wrapper.get_pv_value(self._get_pv_name("readpv"))

    def doStart(self, value):
        self._set_pv(self._get_pv_name("writepv"), value)

    def doStatus(self, maxage=0):
        fault = self._read_pv(self._get_pv_name("isfault"))
        if fault:
            return status.ERROR, fault

        homed = self._read_pv(self._get_pv_name("ishomed"))
        if not homed:
            return status.ERROR, "Not homed"

        busy = self._read_pv(self._get_pv_name("ispumping"))
        if busy:
            return status.BUSY, "Pumping"

        return status.OK

    def doReference(self):
        self._set_pv(self._get_pv_name("reference"), 1)

    def doWriteInnerdiameter(self, value):
        self._set_pv(self._get_pv_name("innerdiameter_sp"), value)
        return value

    def doWriteMaxStroke(self, value):
        self._set_pv(self._get_pv_name("maxstroke_sp"), value)
        return value

    def doWritemaxpressure(self, value):
        self._set_pv(self._get_pv_name("maxpressure_sp"), value)
        return value

    def doWriteStepsize(self, value):
        self._set_pv(self._get_pv_name("stepsize_sp"), value)
        return value

    @usermethod
    def aspirate_step(self):
        self._set_pv(self._get_pv_name("aspiratestep"), 1)

    @usermethod
    def dispense_step(self):
        self._set_pv(self._get_pv_name("dispensestep"), 1)

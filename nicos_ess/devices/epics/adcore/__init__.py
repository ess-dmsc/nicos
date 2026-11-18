"""Image channels for EPICS areaDetector cameras, used with a stock NICOS
Detector."""

from nicos_ess.devices.epics.adcore.base import AreaDetector
from nicos_ess.devices.epics.adcore.orca import OrcaFlash4
from nicos_ess.devices.epics.adcore.timepix import TimepixDetector

__all__ = ["AreaDetector", "OrcaFlash4", "TimepixDetector"]

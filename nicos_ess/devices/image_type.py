"""Image key of a tomography experiment, which NXtomo calls ``image_key``.

The user sets the key before each count, and the key is written to the file
together with the images.
"""

import time

from nicos.core import SIMULATION, CacheError, Override, status, usermethod
from nicos.devices.generic import ManualSwitch

PROJECTION, FLATFIELD, DARKFIELD, INVALID = 0, 1, 2, 3


class ImageType(ManualSwitch):
    """Image type of the next images, which is a projection, flat field or
    dark field."""

    parameter_overrides = {
        "fmtstr": Override(default="%d"),
        "states": Override(
            mandatory=False, default=list(range(PROJECTION, INVALID + 1))
        ),
        "maxage": Override(default=0),
        "pollinterval": Override(default=None, userparam=False, settable=False),
    }

    hardware_access = False

    _image_key_to_image_type = {
        PROJECTION: "Projection",
        FLATFIELD: "Flat field",
        DARKFIELD: "Dark field",
        INVALID: "Invalid",
    }

    def doStatus(self, maxage=0):
        if self.target == INVALID:
            return status.WARN, "State is invalid for a tomography experiment."
        return status.OK, self._image_key_to_image_type[self.target]

    def doStart(self, target):
        ManualSwitch.doStart(self, target)
        if self._mode != SIMULATION:
            if not self._cache:
                raise CacheError(
                    self,
                    "Detector requires a running cache for "
                    "full functionality. Please check its status.",
                )
            curr_time = time.time()
            self._cache.put(self._name, "value", target, curr_time)
            self._cache.put(self._name, "status", self.doStatus(), curr_time)

    @usermethod
    def set_to_projection(self):
        """Set the image key to projection"""
        self.move(PROJECTION)

    @usermethod
    def set_to_flat_field(self):
        """Set the image key to flat field"""
        self.move(FLATFIELD)

    @usermethod
    def set_to_dark_field(self):
        """Set the image key to dark field"""
        self.move(DARKFIELD)

    @usermethod
    def set_to_invalid(self):
        """Set the image key to invalid"""
        self.move(INVALID)

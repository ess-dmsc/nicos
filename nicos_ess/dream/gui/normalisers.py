from enum import Enum

import numpy as np


class NormaliserType(Enum):
    NONORMALISER = 0
    INTEGRAL = 1  # area under curve


class NoNormaliser:
    def normalise(self, y, x):
        return y


class IntegralNormaliser:
    def normalise(self, y, x):
        if not np.any(y):
            # if all entries are zero return the original array
            return y
        integ = np.trapz(y, x)
        if integ == 0:
            # Don't normalize if area under curve is zero.
            return y
        return y / integ


class NormaliserFactory:
    _available_normalisers = {
        NormaliserType.NONORMALISER: NoNormaliser,
        NormaliserType.INTEGRAL: IntegralNormaliser,
    }

    @classmethod
    def create(cls, norm):
        if norm in cls._available_normalisers:
            return cls._available_normalisers[norm]()
        raise NotImplementedError(f"Unknown normaliser type: {norm}")

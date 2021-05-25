
import numpy as np

from nicos.devices.datasinks.image import ImageFileReader


class NumpyFileReader(ImageFileReader):
    filetypes = [
        ('numpy', 'Numpy File (*.npy)'),
    ]

    @classmethod
    def fromfile(cls, filename):
        try:
            return np.load(filename)
        except Exception as error:
            raise NicosError('Unable to open numpy file..')

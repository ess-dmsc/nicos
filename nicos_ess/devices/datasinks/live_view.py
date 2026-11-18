"""Live view sink that sends reduced frames to the clients.

NICOS pushes every live image to every client without backpressure. A full
camera frame every second is more than a remote client can keep up with, and
2048 x 2048 uint16 is already 8 MB. This sink combines bins until a frame has
at most ``maxpoints`` bins and sends the data in the smallest type that holds
it. Counts are summed and other values are averaged. Files and other sinks
get the full arrays.

Each array is sent with everything needed to draw it, which means named dims,
units, bin edges or centres, errors and how the bins were combined. The format
is in `live_frame.encode`. A channel describes its frames with a
`live_frame.LiveArrayDesc` as ``arraydesc``. A plain `ArrayDesc` gives a
picture in pixels.
"""

from dataclasses import replace
from time import time as currenttime

import numpy

from nicos import session
from nicos.core import LIVE, Param, intrange
from nicos.devices.datasinks.special import LiveViewSink, LiveViewSinkHandler
from nicos.utils import byteBuffer
from nicos_ess.utilities.frame_reduction import reduce
from nicos_ess.utilities.live_frame import encode, frame_of


def with_saturation(frame):
    """Record the number of pixels at the maximum of an integer type in ``meta``.

    This has to happen before the bins are combined, because combined bins hide
    saturated pixels.
    """
    data = frame.data
    top = numpy.iinfo(data.dtype).max if data.dtype.kind in "iu" else None
    if top is not None and (saturated := int(numpy.count_nonzero(data == top))):
        return replace(frame, meta={**frame.meta, "saturated": saturated})
    return frame


class ReducedLiveViewSinkHandler(LiveViewSinkHandler):
    def putResults(self, quality, results):
        result = results.get(self.detector.name)
        if result is None:
            return
        arrays = self.processArrays(result)
        descs = list(self.detector.arrayInfo())
        if len(descs) != len(arrays):
            descs = [None] * len(arrays)
        frames = []
        for array, desc in zip(arrays, descs, strict=True):
            if array is None:
                continue
            try:
                frame = with_saturation(frame_of(array, desc))
                frames.append(reduce(frame, self.sink.maxpoints))
            except ValueError as err:
                # Raising would abort the count, and the files get the array anyway.
                self.log.warning("the live view cannot show an array: %s", err)
        if not frames:
            return
        datadescs, databuffers, labelbuffers = encode(frames)
        parameters = dict(
            uid=self.dataset.uid,
            time=currenttime() - self.dataset.started,
            det=self.detector.name,
            tag=LIVE,
            datadescs=datadescs,
        )
        session.updateLiveData(
            parameters,
            [byteBuffer(b) for b in databuffers],
            [byteBuffer(b) for b in labelbuffers],
        )


class ReducedLiveViewSink(LiveViewSink):
    """`LiveViewSink` that sends reduced frames with their axes and units."""

    parameters = {
        "maxpoints": Param(
            "Maximum number of bins in a frame sent to clients. Larger frames get "
            "their bins combined, and the longest side is halved first",
            type=intrange(256, 2**24),
            default=512 * 512,
            settable=True,
        ),
    }

    handlerclass = ReducedLiveViewSinkHandler

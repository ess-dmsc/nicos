"""Live view sink that sends clients reduced images.

NICOS pushes every live image to every client with no backpressure, and a
full camera frame (8 MB for 2048 x 2048 uint16) per second is more than a
remote client keeps up with. This sink combines bins until an array has at
most ``maxpoints`` of them (counts summed) and sends them in the smallest type
that holds them; the axes keep counting source pixels. Files and other sinks
get the full arrays.
"""

from time import time as currenttime

from nicos import session
from nicos.core import LIVE, Param, intrange
from nicos.devices.datasinks.special import LiveViewSink, LiveViewSinkHandler
from nicos.utils import byteBuffer
from nicos_ess.utilities.frame_reduction import reduce
from nicos_ess.utilities.live_frame import encode, frame_of


class ReducedLiveViewSinkHandler(LiveViewSinkHandler):
    def putResults(self, quality, results):
        result = results.get(self.detector.name)
        if result is None:
            return
        frames = [
            reduce(frame_of(array), self.sink.maxpoints)
            for array in self.processArrays(result)
            if array is not None
        ]
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
    """`LiveViewSink` that sends large arrays with bins combined."""

    parameters = {
        "maxpoints": Param(
            "Most bins in one array sent to clients; larger arrays have bins "
            "combined, the longest side halved first",
            type=intrange(256, 2**24),
            default=512 * 512,
            settable=True,
        ),
    }

    handlerclass = ReducedLiveViewSinkHandler

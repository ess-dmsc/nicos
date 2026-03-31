import json
import threading
import time
from dataclasses import asdict

import numpy as np
from streaming_data_types import serialise_da00, serialise_hs01
from streaming_data_types.dataarray_da00 import Variable

from nicos_ess.devices.datasources.livedata_utils import JobId, WorkflowId


DEFAULT_WORKFLOW_ID = WorkflowId(
    instrument="dummy",
    namespace="detector_data",
    name="panel_0_tof",
    version=1,
)
DEFAULT_JOB_ID = JobId(source_name="panel_0", job_number="job-1")


def start_daemon(target):
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread


def make_jbi_histogram(image, total):
    return serialise_hs01(
        {
            "source": image.name,
            "timestamp": int(time.time() * 1000),
            "current_shape": [image.num_bins],
            "dim_metadata": [
                {
                    "length": image.num_bins,
                    "bin_boundaries": np.arange(image.num_bins + 1, dtype=np.int64),
                    "unit": "us",
                    "label": "tof",
                }
            ],
            "data": np.full(
                (image.num_bins,), total / image.num_bins, dtype=np.float64
            ),
            "info": json.dumps(
                {
                    "id": image._unique_id,
                    "state": "COUNTING",
                    "rate": 0.0,
                }
            ),
        }
    )


def make_da00_message(
    output_name,
    total,
    *,
    workflow_id=DEFAULT_WORKFLOW_ID,
    job_id=DEFAULT_JOB_ID,
    timestamp_ns=123456789,
):
    source_name = json.dumps(
        {
            "workflow_id": asdict(workflow_id),
            "job_id": asdict(job_id),
            "output_name": output_name,
        }
    )
    first = total // 3
    second = total // 3
    third = total - first - second
    signal = np.array([first, second, third], dtype=np.int32)
    return serialise_da00(
        source_name=source_name,
        timestamp_ns=timestamp_ns,
        data=[
            Variable(
                name="signal",
                data=signal,
                shape=signal.shape,
                axes=["tof"],
                unit="counts",
                label=f"Detector signal {output_name}",
            ),
            Variable(
                name="tof",
                data=np.array([0.0, 1.0, 2.0], dtype=np.float64),
                shape=(3,),
                axes=["tof"],
                unit="ms",
                label="TOF",
            ),
        ],
    )


def stop_messages(producer):
    return [
        message
        for message in producer.messages
        if message["message"] == b'{"cmd": "stop"}'
    ]

description = "Lambert HiCAM Fluo Intensifier"
group = "optional"

includes = []

tango_base = "tango://antareslamcam.office.frm2.tum.de:10000/antares/hicamfluo/"

devices = dict(
    file_index=device(
        "nicos.devices.entangle.DigitalOutput",
        description="File number",
        tangodevice=tango_base + "file_index",
        fmtstr="%.0f",
        pollinterval=5,
        maxage=5,
    ),
    acquisition_time=device(
        "nicos.devices.entangle.AnalogOutput",
        description="Total acquisition time",
        tangodevice=tango_base + "total_exp_time",
        unit="s",
        fmtstr="%.1f",
        pollinterval=5,
        maxage=5,
    ),
    exposure_time=device(
        "nicos.devices.entangle.AnalogOutput",
        description="Exposure time per frame",
        tangodevice=tango_base + "exp_time_per_frame",
        unit="µs",
        fmtstr="%.1f",
        pollinterval=5,
        maxage=5,
    ),
    step_count=device(
        "nicos.devices.entangle.DigitalOutput",
        description="Number of steps.",
        tangodevice=tango_base + "steps",
        fmtstr="%.0f",
        pollinterval=5,
        maxage=5,
    ),
    acquire=device(
        "nicos.devices.entangle.NamedDigitalOutput",
        description="Start acquisition",
        tangodevice=tango_base + "acquire",
        mapping=dict(Reset=0, Acquire=1, Done=2),
        pollinterval=0.5,
        maxage=1,
    ),
    elapsed_time=device(
        "nicos.devices.entangle.Sensor",
        description="Elapsed time since acquisition start",
        tangodevice=tango_base + "elapsed_time",
        unit="s",
        pollinterval=0.5,
        maxage=0,
    ),
)

"""User commands for Kafka-controlled NeXus file-writing jobs."""

from contextlib import contextmanager

from nicos import session
from nicos.commands import helparglist, parallel_safe, usercommand
from nicos.core import ADMIN, SIMULATION, requires

from nicos_ess.devices.datasinks.file_writer import FileWriterControlSink

__all__ = [
    "nexusfile_open",
    "start_filewriting",
    "stop_filewriting",
    "list_filewriting_jobs",
    "replay_job",
]


def _find_filewriter_dev():
    for dev in session.devices.values():
        # Should only be one at most
        if isinstance(dev, FileWriterControlSink):
            return dev
    raise RuntimeError("Could not find FileWriterControlSink device")


@usercommand
@helparglist("run_title")
@contextmanager
def nexusfile_open(run_title=None):
    """Submit one File Writer job for the duration of a ``with`` block.

    The command sends the start request before entering the block and sends a
    stop timestamp when the block exits. The File Writer can continue consuming
    messages after the stop request, so use :func:`list_filewriting_jobs` to
    confirm completion.

    If *run_title* is omitted, the current experiment run title is used.
    Nested calls share the outer job; an inner call does not start or stop a
    second job.

    Errors raised in the block are logged and are not re-raised.

    Example::

        with nexusfile_open('Motor alignment'):
            scan(motor, 0, 1, 11, timer=10)
    """
    nested_call = False
    if run_title is None:
        run_title = session.experiment.run_title
    try:
        active_jobs = _find_filewriter_dev().get_active_jobs()
        if not active_jobs:
            session.log.info("Setting run title to: %s", run_title)
            start_filewriting(run_title)
        else:
            #  Allow nested calls, but give a warning since it is not
            #  a preferred way of writing scripts
            session.log.warning(
                "Filewriter already running. Will not start a new file with title: %s",
                run_title,
            )
            nested_call = True
        yield
    except Exception as e:
        session.log.error("Could not start filewriting: %s", e)
        session.log.warning("The rest of the batch file code will be ignored.")
    finally:
        if not nested_call:
            stop_filewriting()
        else:
            session.log.warning(
                "Since this context did not start the "
                "filewriter for file with title: %s, "
                "it will not attempt to stop the "
                "filewriter either",
                run_title,
            )


@usercommand
@helparglist("run_title")
def start_filewriting(run_title=None):
    """Submit a File Writer job, optionally setting its run title.

    A proposal must be selected and no other job may be active.
    """
    if run_title is not None and session.mode != SIMULATION:
        session.experiment.run_title = run_title
    _find_filewriter_dev().start_job()


@usercommand
@helparglist("job_number")
def stop_filewriting(job_number=None):
    """Request that a File Writer job stop at the current time.

    :param job_number: Job number to stop. It is required when more than one
        job is active.
    """
    _find_filewriter_dev().stop_job(job_number)


@usercommand
@parallel_safe
def list_filewriting_jobs():
    """List current and recent jobs with their state and first error."""
    _find_filewriter_dev().list_jobs()


@usercommand
@requires(level=ADMIN)
@helparglist("job_number")
def replay_job(job_number):
    """Submit a new job for a completed job's original data window.

    The source Kafka topics must still retain the data.

    :param job_number: Number of the job to replay.
    """
    _find_filewriter_dev().replay_job(job_number)

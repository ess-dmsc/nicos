from contextlib import contextmanager

from nicos import session
from nicos.commands import helparglist, usercommand
from nicos.core import ADMIN, SIMULATION, requires, waitForCompletion
from nicos_ess.commands.scichat import scichat_send

from nicos_ess.devices.datasinks.file_writer import Filewriter


def _find_filewriter_dev():
    for dev in session.devices.values():
        # Should only be one at most
        if isinstance(dev, Filewriter):
            return dev
    raise RuntimeError("Could not find Filewriter device")


@usercommand
@helparglist("run_title")
@contextmanager
def nexusfile_open(run_title=None):
    """Command that creates a nexusfile and starts writing data to it
    for as long as your script is running within the indentation.

    Upon completing the code within the indented block the file writing
    will stop. This is the main command that should be used when you
    want to write nexusfiles.

    For example:

    >>> with nexusfile_open('motor_dataset'):
    >>>     maw(Motor, 35)     # write scan code in indented block

    , would create a nexusfile with the title 'motor_dataset' and then
    record data for as long as the Motor device is moving. Upon reaching
    the end of the indented code block the data recording will stop.

    It is possible to make a nested call of the command, but it is
    not adviced. It will still only create one file which
    is the one that was started with the first command call.
    """
    nested_call = False
    if run_title is None:
        run_title = session.experiment.run_title
    try:
        active_job = _find_filewriter_dev().get_active_job()
        if not active_job:
            session.log.info("Setting run title to: %s", run_title)
            start_filewriting(run_title)
        else:
            #  Allow nested calls, but give a warning since it is not
            #  a preferred way of writing scripts
            session.log.warning(
                "Filewriter already running. "
                "Will not start a new file with title: %s",
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
    """Start a file-writing job."""
    if run_title is not None and session.mode != SIMULATION:
        session.experiment.run_title = run_title
    dev = _find_filewriter_dev()
    dev.start_job()
    message = (
        "Starting filewriting\n"
        f"  Title: {session.experiment.run_title}\n"
        f"  Run number: {session.experiment.get_current_run_number()}"
    )
    scichat_send(message)
    waitForCompletion(dev)


@usercommand
@helparglist("job_number")
def stop_filewriting():
    """Stop a file-writing job."""
    dev = _find_filewriter_dev()
    dev.stop_job()
    scichat_send("stopping filewriting")
    waitForCompletion(dev)


@usercommand
def list_filewriting_jobs():
    """List current and recent file-writing jobs."""
    _find_filewriter_dev().list_jobs()


@usercommand
@requires(level=ADMIN)
@helparglist("job_number")
def replay_job(job_number):
    """Replay a recent file-writing job.

    :param job_number: the number of the job to replay.
    """
    dev = _find_filewriter_dev()
    dev.replay_job(job_number)
    waitForCompletion(dev)

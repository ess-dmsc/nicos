from nicos.commands import usercommand

__all__ = ["do_trans", "do_sans", "do_simultaneous"]


@usercommand
def do_trans(trans_duration=None, trans_duration_type=None):
    raise NotImplementedError("Please implement do_trans script")


@usercommand
def do_sans(sans_duration=None, sans_duration_type=None):
    raise NotImplementedError("Please implement do_sans script")


@usercommand
def do_simultaneous(sans_duration=None, sans_duration_type=None):
    raise NotImplementedError("Please implement do_simultanous script")

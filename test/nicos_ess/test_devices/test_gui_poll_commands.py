"""The poll commands that the ESS device dialogs send, run on a real device."""

import pytest

from nicos.protocols.cache import FLAG_NO_STORE

session_setup = "axis"

ASYNC = "motor.asyncPollVolatileParams()"
REFRESH_ONE = "session.getDevice('motor').pollParams('ramp')"
REFRESH_ALL = "session.getDevice('motor').pollParams()"


def run(session, command):
    return eval(command, {"session": session, "motor": session.getDevice("motor")})


def test_async_poll_asks_the_poller_for_volatile_params(session, monkeypatch):
    motor = session.getDevice("motor")
    sent = []
    monkeypatch.setattr(
        type(motor._cache),
        "put_raw",
        lambda _cache, key, value, **kw: sent.append((key, value, kw)),
    )

    run(session, ASYNC)

    assert sent == [("poller/motor/pollparams", ["ramp"], {"flag": FLAG_NO_STORE})]


@pytest.mark.parametrize("command", [REFRESH_ONE, REFRESH_ALL])
def test_refresh_reads_the_param_right_away(session, command):
    motor = session.getDevice("motor")
    motor._setROParam("ramp", 0)
    motor.speed = 2

    run(session, command)

    assert motor._cache.get(motor, "ramp") == 120

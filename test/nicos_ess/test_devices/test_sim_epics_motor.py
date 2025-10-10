import sys

import pytest
import threading

from nicos.commands.basic import sleep
from nicos.commands.device import maw, move, waitfor


@pytest.fixture(scope="class")
def motor():
    from test.nicos_ess.test_devices.p4p_motor_sim import main as sim_main
    # start the motor simulator in thread

    def target():
        argv0 = sys.argv
        sys.argv = ["sim-motor", "--prefix", "SIM:M1"]  # add flags if you want
        try:
            sim_main()
        finally:
            sys.argv = argv0

    motor_thread = threading.Thread(target=target, daemon=True)
    motor_thread.start()
    yield
    motor_thread.join(timeout=1)


session_setup = "ess_sim_motors"



def test_motor(motor, session):
    motor_1 = session.getDevice("motor_1")
    # start at 0
    assert motor_1.read(0) == 0
    # move to 2
    maw("motor_1", 1.2)
    assert motor_1.read(0) == 1.2

    # assert limits are working
    assert motor_1.abslimits == (-1000.0, 1000.0)
    assert motor_1.userlimits == (-1000.0, 1000.0)

    while not motor_1.isCompleted():
        sleep(0.01)

    # apply an offset
    motor_1.offset = 0.5
    assert motor_1.read(0) == 1.7  # 1.2 + 0.5

    # check that abslimits are unchanged
    assert motor_1.abslimits == (-1000.0, 1000.0)
    # check that userlimits have changed
    assert motor_1.userlimits == (-999.5, 1000.5)

    while not motor_1.isCompleted():
        sleep(0.01)

    # apply negative offset
    motor_1.offset = -0.5
    assert motor_1.read(0) == 0.7  # 1.2 - 0.5

    # check that abslimits are unchanged
    assert motor_1.abslimits == (-1000.0, 1000.0)
    # check that userlimits have changed
    assert motor_1.userlimits == (-1000.5, 999.5)





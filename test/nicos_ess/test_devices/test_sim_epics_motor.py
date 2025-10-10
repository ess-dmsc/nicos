import sys

import pytest
import threading

from nicos.commands.basic import sleep
from nicos.commands.device import maw, move


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
    move(motor_1, 2)
    sleep(5)
    print(motor_1.read(0))
    assert abs(motor_1.read(0) - 2) < 0.01


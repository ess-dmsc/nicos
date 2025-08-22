"""
LOKI script to move the detector carriage, controlling the PS bank (disable/enable).

Example usage in nicos shell:
>> DET_POS=20; run("/path/to/nicos/nicos_ess/loki/testscripts/move_det.py")
"""

from nicos.core import NicosError

if DET_POS is None:
    raise NicosError("DET_POS variable is not set. Please set a value for it.")

# 1. Disable PS Bank, if needed
if HV_Bank_0.status_on()[0]:
    print("Disabling PS Bank...")
    disable(HV_Bank_0)
    sleep(0.3)
    while (HV_Bank_0.status_on()[0]):
        sleep(1)

# 2. Wait voltage zero, if needed
if not detector_carriage.bank_voltage_is_zero():
    print("Waiting for voltages to be zero...")
    while not detector_carriage.bank_voltage_is_zero():
        sleep(1)

move(detector_carriage, DET_POS)

# 3. Re-enable PS Bank (OPTIONAL, uncomment if needed)
#print("Re-enabling detector PS bank...")
#enable(HV_Bank_0)

# 4. Clean variable to avoid undesired past positions
DET_POS = None
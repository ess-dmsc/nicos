# ruff: noqa: F821
"""
LOKI script to move the detector carriage, controlling the PS bank (disable/enable).

Example usage in NICOS shell:
>> DET_POS=20; run("/ess/ecdc/nicos-core/nicos_ess/loki/testscripts/move_det.py")
"""

from nicos.core import NicosError, status

# 0. Variable check
try:
    target_position = DET_POS
except NameError:
    target_position = None

if target_position is None:
    raise NicosError("DET_POS variable is not set. Please set a value for it.")

# 1. Disable the power-supply group
if hv_bank0.status()[0] != status.DISABLED:
    print("Disabling PS Bank...")
    disable(hv_bank0)

# 2. Wait until the group is disabled and its voltage has decayed
power_status, message = hv_bank0.status()
while power_status != status.DISABLED:
    if power_status in (status.ERROR, status.UNKNOWN):
        raise NicosError(f"Cannot make the detector safe: {message}")
    print(f"Waiting for the power supply to switch off: {message}")
    sleep(1)
    power_status, message = hv_bank0.status()

voltages = hv_bank0.read()
if not isinstance(voltages, tuple):
    voltages = (voltages,)
while (
    max(abs(voltage) for voltage in voltages) > detector_carriage.voltage_off_threshold
):
    print("Waiting for power-supply voltages to decay...")
    sleep(1)
    voltages = hv_bank0.read()
    if not isinstance(voltages, tuple):
        voltages = (voltages,)

move(detector_carriage, target_position)

# 3. Re-enable PS Bank (OPTIONAL, uncomment if it's needed and safe)
# print("Re-enabling detector PS bank...")
# enable(hv_bank0)

# 4. Clean variable to avoid undesired past positions
DET_POS = None

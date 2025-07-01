"""
LOKI collimation scans using single blades

Requires: collimation system and virtual detector 
configurations loaded.

Case: Scan gap width
"""


# User defined vars
BLADE_1 = slit_set_1_left_blade  # Test 3.5 (in x direction)
BLADE_2 = slit_set_1_right_blade
#BLADE_1 = slit_set_1_upper_blade  # Test 3.6 (in y direction)
#BLADE_2 = slit_set_1_bottom_blade
START = 1
STEP = 1
WAIT_TIME = 5
LIMIT = 41  # Upper limit of BLADE_2

start_pos_1 = START
start_pos_2 = LIMIT
step_size_1 = STEP
step_size_2 = -STEP # Opposite direction, closing
num_of_points = abs(START - start_pos_2)

SetDetectors(timer_detector) # Virtual_detector should be loaded too
scan([BLADE_1, BLADE_2], [start_pos_1, start_pos_2], [step_size_1, step_size_2], num_of_points, timer=WAIT_TIME)
#***********************************************
# COLLIMATION SYSTEM INTEGREATED TEST
# 26 JUNE 2025
# SCRIPT FOR SCAN TEST
#***********************************************

# Test 3.3
BLADE_1 = slit_set_1_left_blade
BLADE_2 = slit_set_1_right_blade

# Test 3.4
#BLADE_1 = slit_set_1_upper_blade
#BLADE_2 = slit_set_1_bottom_blade

START = 1 
STEP = 1
GAP_SIZE = 5
SLEEP_TIME = 3
LIMIT = 41  # Upper limit of BLADE_2

pos1 = START  # BLADE_1 position
pos2 = START + GAP_SIZE  # BLADE_2 position

loop_num = 1
while(pos2 < LIMIT):
    print("Loop " + str(loop_num))

    move(BLADE_1, pos1)
    move(BLADE_2, pos2)

    print("Moving...")
    wait(BLADE_1, BLADE_2)

    sleep(SLEEP_TIME)

    pos1 += STEP
    pos2 += STEP
    loop_num += 1

print("Scan done!")
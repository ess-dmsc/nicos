# pylint: skip-file

# test: subdirs = loki
# test: setups = bandwidth_choppers, beam_monitors, beamstops, collimation_systems, frame_overlap_choppers, laser_mirror, motion_cabinet_1, motion_cabinet_2, motion_cabinet_3, motion_cabinet_4, motion_cabinet_5, sample_holder, sample_stack, window_guard
# test: setupcode = thermostated_sample_holder.cartridges = [{"labels": ["sim_cell"], "positions": [(0, 0)]}]
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

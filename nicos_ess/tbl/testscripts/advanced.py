# pylint: skip-file

# test: subdirs = tbl
# test: setups = adjustable_collimator, bwc_choppers, filter_station, motion_cabinet_1, motion_cabinet_2, motion_cabinet_3, motion_cabinet_4, just_bin_it
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(jbi_detector)
with nexusfile_open("test title"):
    scan(axis_horizontal, 0, 10, 11)

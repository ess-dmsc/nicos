# pylint: skip-file

# test: subdirs = dream
# test: setups = choppers, collimation_slits, sample_position_stack, just-bin-it
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(jbi_detector)
with nexusfile_open("test title"):
    scan(pos_x, 0, 10, 11)

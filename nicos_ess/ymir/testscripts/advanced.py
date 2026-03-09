# pylint: skip-file

# test: subdirs = ymir
# test: setups = alignment_stack, choppers, motion_cabinet_1, motion_cabinet_2, just-bin-it
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(det)
with nexusfile_open("test title"):
    scan(mX, 0, 10, 11)

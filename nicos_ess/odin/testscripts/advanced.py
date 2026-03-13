# pylint: skip-file

# test: subdirs = odin
# test: setups = motion_cabinet_1, motion_cabinet_2, motion_cabinet_3, motion_cabinet_4, motion_cabinet_5, just_bin_it
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(jbi_detector)
with nexusfile_open("test title"):
    scan(wfmc_translation, 0, 10, 11)

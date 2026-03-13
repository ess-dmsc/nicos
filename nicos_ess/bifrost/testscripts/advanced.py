# pylint: skip-file

# test: subdirs = bifrost
# test: setups = bwc_choppers, foc_choppers, motion_cabinet_1, motion_cabinet_2, motion_cabinet_3, psc_choppers, sample_slits, just-bin-it
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(jbi_detector)
with nexusfile_open("test title"):
    scan(sample_slit_y_p, 0, 10, 11)

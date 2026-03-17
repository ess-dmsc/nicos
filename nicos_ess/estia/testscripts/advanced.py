# pylint: skip-file

# test: subdirs = estia
# test: setups = bandwith_chopper, middle_focus, motion_cabinet_1, motion_cabinet_2, sample_slit, sg1-cart, sg1-mover, sg1-interferometer, sg2-mover, virtual_source, just-bin-it
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(jbi_device)
with nexusfile_open("test title"):
    scan(mpos1, 0, 10, 11)

# pylint: skip-file

# test: subdirs = demo
# test: setups = area_detector
# test: needs = streaming_data_types
# test: needs = confluent_kafka
# test: needs = yuos_query

read()
status()

SetDetectors(area_detector)

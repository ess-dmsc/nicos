#!/bin/bash

(
  echo "Waiting for Kafka to be ready..."
  sleep 10  # Wait for Kafka to fully start

  declare -a topics=(
    "ess_filewriter_pool:1:1"
    "ess_filewriter_status:1:1"
    "nmx_choppers:1:1"
    "nmx_detector_p0:1:1"
    "nmx_detector_p1:1:1"
    "nmx_detector_p2:1:1"
    "nmx_motion:1:1"
    "nmx_nicos_devices:1:1"
  )

  for topicConfig in "${topics[@]}"; do
    IFS=':' read -r topicName partitions replicationFactor <<< "$topicConfig"
    echo "Creating topic: $topicName with $partitions partitions and $replicationFactor replication factor"
    kafka-topics.sh --create --bootstrap-server localhost:9092 \
      --replication-factor "$replicationFactor" --partitions "$partitions" --topic "$topicName" || {
        echo "Failed to create topic $topicName. Retrying..."
        sleep 5
        kafka-topics.sh --create --bootstrap-server localhost:9092 \
          --replication-factor "$replicationFactor" --partitions "$partitions" --topic "$topicName"
      }
  done

  echo "Topic creation completed."
) &

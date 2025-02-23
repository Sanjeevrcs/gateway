import os
import sys
sys.path = [p for p in sys.path if p != os.path.abspath('kafka')]
from kafka import KafkaProducer
import json
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka configuration
# Use environment variable or default to docker network
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'localhost:9092')


def create_kafka_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER_URL,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        return producer
    except Exception as e:
        logger.error(f"Error creating Kafka producer: {e}")
        return None

def produce_event(data):
    
    json_data = json.loads(data)
    tenant_id = json_data['tenant_id']
    gateway_id = json_data['gateway_id']
    TOPIC_NAME = f"tenant_{tenant_id}"
    print(f"Producing event to topic: {TOPIC_NAME}")
    producer = create_kafka_producer()
    if not producer:
        logger.error("Failed to create producer")
        return

    try:

        # Ensure data is in the correct format
        message = {
            "data": data,
            "gateway_id": gateway_id
        }
        # Send message
        future = producer.send(TOPIC_NAME, message)
        
        # Block until a single message is sent (optional)
        record_metadata = future.get(timeout=10)
        
        logger.info(f"Message sent to topic '{record_metadata.topic}' "
                    f"Partition: {record_metadata.partition} "
                    f"Offset: {record_metadata.offset}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
    finally:
        # Always close the producer
        producer.close()
import os
from kafka import KafkaConsumer
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka configuration
# Use environment variable or default to docker network
KAFKA_BROKER_URL = 'localhost:9092'
TOPIC_NAME = 'petronas'

def create_kafka_consumer():
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=KAFKA_BROKER_URL,
            auto_offset_reset='earliest',  # Start consuming from the beginning of the topic
            enable_auto_commit=True,
            group_id='sample-group',  # Consumer group ID
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))  # Deserialize messages as JSON
        )
        
        logger.info(f"Connected to Kafka broker at {KAFKA_BROKER_URL}")
        logger.info(f"Subscribed to topic: {TOPIC_NAME}")
        
        return consumer
    except Exception as e:
        logger.error(f"Error connecting to Kafka: {e}")
        return None

def main():
    consumer = create_kafka_consumer()
    if not consumer:
        logger.error("Failed to create Kafka consumer")
        return

    logger.info("Starting consumer...")
    try:
        for message in consumer:
            logger.info(f"Received message: {message.value}")
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Error in consumer: {e}")
    finally:
        if consumer:
            consumer.close()

if __name__ == '__main__':
    main()
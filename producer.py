#!/usr/bin/env python

from random import choice
from confluent_kafka import Producer

# Configuration settings
config = {
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all'
}

# Create Producer instance
producer = Producer(config)

# Topic
topic = "quickstart"

# Callback function for delivery
def delivery_callback(err, msg):
    if err:
        print('ERROR: Message failed delivery: {}'.format(err))
    else:
        # print("Produced event to topic {topic}".format(
        #     topic=msg.topic()))
        pass

# Function to produce an event
def produce_event(data):
    producer.produce(topic, data, callback=delivery_callback)
    producer.poll(0)
    producer.flush()



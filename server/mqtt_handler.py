import paho.mqtt.client as mqtt
import logging
from typing import Callable

logging.basicConfig(level=logging.INFO)

class MQTTHandler:
    """Handles MQTT client setup, connections, and message reception."""

    def __init__(self, broker: str, port: int, topic: str, on_message_callback: Callable):
        """
        Initializes the MQTT connection.
        :param broker: MQTT Broker address
        :param port: MQTT Broker port
        :param topic: MQTT topic to subscribe to
        :param on_message_callback: Callback function for handling messages
        """
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()

        # Attach callback for message handling
        self.client.on_message = on_message_callback

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.subscribe(self.topic)
            logging.info(f"Connected to MQTT Broker at {self.broker}:{self.port}, subscribed to {self.topic}")
        except Exception as e:
            logging.error(f"Failed to connect to MQTT Broker: {e}")

    def start(self):
        """Starts the MQTT loop to keep listening for messages."""
        logging.info("Listening for MQTT messages...")
        self.client.loop_forever()

    def publish(self, topic: str, message: str):
        """Publishes a message to a specific topic."""
        result, mid = self.client.publish(topic, message)
        if result == mqtt.MQTT_ERR_SUCCESS:
            logging.info(f"Message '{message}' published to {topic}")
        else:
            logging.error(f"Failed to publish message to {topic}")

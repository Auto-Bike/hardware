import logging
import json
from server.mqtt_handler import MQTTHandler
from Motor.motor import MotorController
from server.config.motor_config import MOTORS  # Import motor-related config
from server.config.server_config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, BIKE_ID  # Import server settings



logging.basicConfig(level=logging.INFO)

class BikeClient:
    """Handles bike-specific MQTT message processing."""

    def __init__(self):
        """Initializes the bike and sets up MQTT communication."""
        self.mqtt_handler = MQTTHandler(
            MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, self.on_mqtt_message
        )
        self.big_motor = MotorController(MOTORS["big_motor"])
        self.small_motor = MotorController(MOTORS["small_motor"])


    def on_mqtt_message(self, client, userdata, message):
        """Handles incoming MQTT messages."""
        payload = json.loads(message.payload.decode().strip())  # Convert to JSON
        print(payload)
        command = payload.get("command", "stop")  # Default to stop if missing
        speed = payload.get("speed", 50)  # Default to 50% speed
        
        match command:
          case "forward":
            logging.info("Moving Forward")
            self.big_motor.motor_control("forward", speed)  # Default speed 50%

          case "backward":
              logging.info("Moving Backward")
              self.big_motor.motor_control("reverse", speed)

          case "left":
              logging.info("Turning Left")
            #   self.small_motor.motor_control("left", speed)  # Custom left turn logic

          case "right":
              logging.info("Turning Right")
            #   self.small_motor.motor_control("right", speed)  # Custom right turn logic

          case "stop":
              logging.info("Stopping")
              self.big_motor.motor_control("stop", 0)
        
        
        # if payload == "connect":
        #     
        #     self.acknowledge_connection()


    def acknowledge_connection(self):
        """Publishes an acknowledgment message to the MQTT broker."""
        ack_topic = f"bike/{BIKE_ID}/status"
        self.mqtt_handler.publish(ack_topic, "connected")
        logging.info(f"Bike {BIKE_ID} acknowledged connection.")

    def start(self):
        """Starts the MQTT client to listen for messages."""
        self.mqtt_handler.start()

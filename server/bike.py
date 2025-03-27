import logging
import json
import time
import threading
from server.mqtt_handler import MQTTHandler
from Motor.motor import MotorController
from server.config.motor_config import MOTORS  # Import motor-related config
from Motor.smallmotor import SmallMotorController
from Redis.redis_manager import RedisManager
from GPS.GPS_reader import SerialGPSReader
from server.config.server_config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC,
    BIKE_ID,
    REDIS_HOST,
)  # Import server settings

logging.basicConfig(level=logging.INFO)


class BikeClient:
    """Handles bike-specific MQTT message processing."""

    def __init__(self):
        """Initializes the bike and sets up MQTT communication."""
        self.mqtt_handler = MQTTHandler(
            MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, self.on_mqtt_message
        )
        self.big_motor = MotorController(MOTORS["big_motor"])
        self.small_motor = SmallMotorController()
        # self.redis_client = redis.Redis(
        #     host=REDIS_HOST, port=6379, db=0, decode_responses=True
        # )
        self.redis = RedisManager(REDIS_HOST, 6379)
        # to add, intialize the GPS reader
        self.gps_reader = SerialGPSReader()
        self.start_gps_thread()
        #

    def on_mqtt_message(self, client, userdata, message):
        """Handles incoming MQTT messages."""
        payload = json.loads(message.payload.decode().strip())  # Convert to JSON
        print(payload)

        command = payload.get("command", "stop")  # Default to stop if missing
        speed = payload.get("speed", 50)  # Default to 50% speed
        turning_angle = payload.get("turning_angle", 0)  # Default to 50% speed

        if command == "connect":
            # Send post request to the server
            self.acknowledge_connection()
            return

        match command:
            case "forward":
                logging.info("Moving Forward")
                self.big_motor.motor_control("forward", speed=speed)

            case "backward":
                logging.info("Moving Backward")
                self.big_motor.motor_control("reverse", speed=speed)

            case "left":
                logging.info("Turning Left")
                # self.small_motor.motor_control("left", time_duration=time_duration)
                self.small_motor.turn_left_by(turning_angle)

            case "right":
                logging.info("Turning Right")
                # self.small_motor.motor_control("right", time_duration=time_duration)
                self.small_motor.turn_right_by(turning_angle)

            case "center":
                logging.info("Centering")
                self.small_motor.center()

            case "stop":
                logging.info("Stopping")
                self.big_motor.motor_control("stop", 0)
                self.small_motor.stop()

    def acknowledge_connection(self):
        """Publishes an acknowledgment message to Redis."""
        self.redis.acknowledge_connection(BIKE_ID)

    def start(self):
        """Starts the MQTT client to listen for messages."""
        self.mqtt_handler.start()

    def start_gps_thread(self):
        def gps_loop():
            while True:
                data = self.gps_reader.read_data()
                if data:
                    payload = {
                        "bike_id": BIKE_ID,
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timestamp": time.time(),
                    }
                    self.redis.push_gps_data(BIKE_ID, payload)
                time.sleep(1)

        gps_thread = threading.Thread(target=gps_loop, daemon=True)
        gps_thread.start()

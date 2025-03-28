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
from Route.route import RoutePlanner
from Route.key import API_KEY
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
        self.small_motor = MotorController(
            MOTORS["small_motor"]
        )  # this is only for testing when esp32 is not connected
        # self.small_motor = SmallMotorController()

        self.redis = RedisManager(REDIS_HOST, 6379)
        # to add, intialize the GPS reader
        self.gps_reader = SerialGPSReader()
        self.start_gps_thread()
        self.route_planner = RoutePlanner(API_KEY)
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

            case "navigate":
                start = payload.get("start")
                destination = payload.get("destination")
                if start and destination:
                    logging.info(
                        f"🧭 Received navigate command:\nStart: {start}\nDestination: {destination}"
                    )
                    self.handle_navigation(start, destination)
                else:
                    logging.warning(
                        "⚠️ 'navigate' command missing start or destination coordinates."
                    )

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

    def estimate_duration(self, distance_meters):
        return distance_meters / self.FORWARD_SPEED_MPS

    TURN_ANGLE = 60  # degrees
    FORWARD_SPEED_MPS = 0.8  # meters/second
    TURN_DURATION_SEC = 5  # time to keep turn before centering (in seconds)

    def execute_turn(self, direction, angle=None, speed=30, forward_duration=None):
        """
        Executes a turn by steering the small motor, moving forward, then centering.
        """
        if angle is None:
            angle = self.TURN_ANGLE
        if forward_duration is None:
            forward_duration = self.TURN_DURATION_SEC

        # 1. Turn the front wheel
        if direction == "LEFT":
            logging.info(f"↪️ Turning LEFT by {angle}°")
            self.small_motor.turn_left_by(angle)
        elif direction == "RIGHT":
            logging.info(f"↩️ Turning RIGHT by {angle}°")
            self.small_motor.turn_right_by(angle)
        else:
            logging.warning(f"⚠️ Invalid turn direction: {direction}")
            return

        # 2. Move forward while in turned state
        logging.info(
            f"🚴 Moving forward during turn for {forward_duration:.2f} seconds at speed {speed}"
        )
        self.big_motor.motor_control("forward", speed)
        time.sleep(forward_duration)
        self.big_motor.motor_control("stop", 0)

        # 3. Center the wheel
        logging.info("🎯 Centering front wheel")
        self.small_motor.center()
        time.sleep(0.5)  # short pause after re-centering

    def handle_navigation(self, start, destination):
        """Handles route planning using start and destination coordinates."""

        try:
            origin = {"latitude": start["lat"], "longitude": start["lon"]}
            dest = {"latitude": destination["lat"], "longitude": destination["lon"]}

            self.route_planner.fetch_route(origin=origin, destination=dest)
            steps = self.route_planner.get_steps()
            print(steps)
            for idx, step in enumerate(steps, 1):
                logging.info(f"[Step {idx}] {step.instruction} ({step.distance} m)")
                logging.info(f"    Start: ({step.start_lat}, {step.start_lng})")
                logging.info(f"    End:   ({step.end_lat}, {step.end_lng})")

                maneuver = step.maneuver.upper()
                print(maneuver)
                if "LEFT" in maneuver:
                    self.execute_turn("LEFT", self.TURN_ANGLE)
                elif "RIGHT" in maneuver:
                    self.execute_turn("RIGHT", self.TURN_ANGLE)
                elif "DEPART" in maneuver or maneuver == "NAME_CHANGE":
                    logging.info("⬆️ Going STRAIGHT")

                duration = self.estimate_duration(step.distance)
                logging.info(f"🚴 Moving forward for approx {duration:.2f} seconds\n")
                self.big_motor.motor_control("forward", speed=30)
                time.sleep(duration)
                self.big_motor.motor_control("stop", speed=0)
                time.sleep(1)

                # several assumptions have to make here
                # 1. the bike would always face the correct direction
                # 2. the turning angle would always stay 60 degrees
                # 3. the turning angle would recover to center after X seconds turning
                # 4. the distance required for turning would be 10 meters
                # 5. the bike would always move forward for 10 meters

            # 🚧 TODO: Add logic to follow each step using motors
        except Exception as e:
            logging.error(f"❌ Route planning failed: {e}")

import time
import json
import threading

from Motor.motor import MotorController
from Motor.config import MOTORS
from Motor.ESP32.main import ESP32SerialReader
from BLT.continuous_steering import ContinuousSteeringController
from Redis.redis_manager import RedisManager
from GPS.GPS_reader import SerialGPSReader
from server.config.server_config import REDIS_HOST, BIKE_ID


class TrajectoryReplayer:
    """
    Replays a recorded sequence of throttle and steering commands,
    with optional live GPS tracking and abort key handling.
    """

    def __init__(
        self,
        filepath,
        motor_controller,
        steering_controller,
        gps_reader=None,
        redis_client=None,
        bike_id="bike-001",
    ):
        self.filepath = filepath
        self.motor = motor_controller
        self.steering = steering_controller
        self.gps_reader = gps_reader
        self.redis = redis_client
        self.bike_id = bike_id
        self.trajectory = []
        self.abort_flag = False

    def load_trajectory(self):
        """Load the recorded trajectory from file."""
        with open(self.filepath, "r") as f:
            self.trajectory = json.load(f)

    def start_gps_tracking(self):
        """Start a background thread for pushing GPS data if gps_reader is provided."""

        def gps_loop():
            while not self.abort_flag:
                if self.gps_reader:
                    data = self.gps_reader.read_data()
                    if data and self.redis:
                        payload = {
                            "bike_id": self.bike_id,
                            "latitude": data.get("latitude"),
                            "longitude": data.get("longitude"),
                            "timestamp": time.time(),
                        }
                        self.redis.push_gps_data(self.bike_id, payload)
                time.sleep(1)

        if self.gps_reader:
            threading.Thread(target=gps_loop, daemon=True).start()

    def play(self):
        """
        Play back the recorded throttle and steering commands
        with timing based on original timestamps.
        """
        if not self.trajectory:
            self.load_trajectory()

        print("🚗 Starting trajectory replay...")
        # self.start_gps_tracking()

        start_time = self.trajectory[0]["timestamp"]
        for i, frame in enumerate(self.trajectory):
            if self.abort_flag:
                break

            now = time.time()
            target_time = now + (frame["timestamp"] - start_time)

            # Send control commands
            throttle = frame["joystick"]["throttle"]
            steering = frame["joystick"]["steering"]

            pwm = int(min(abs(throttle), 1.0) * 70)  # Assuming max PWM is 70
            if throttle > 0:
                self.motor.motor_control("forward", speed=pwm)
            else:
                self.motor.motor_control("reverse", speed=pwm)

            # Convert normalized steering to angle
            center_angle = 150.0
            angle_delta = steering * 60
            self.steering.set_target_angle(center_angle + angle_delta)

            # Wait until it's time for the next frame
            if i < len(self.trajectory) - 1:
                next_ts = self.trajectory[i + 1]["timestamp"]
                delay = next_ts - frame["timestamp"]
                time.sleep(max(0.01, delay))

        print("✅ Trajectory replay finished.")
        self.motor.stop_immediately()
        self.steering.stop()


# Example usage
if __name__ == "__main__":
    esp32 = ESP32SerialReader()
    esp32.connect()

    motor = MotorController(MOTORS["big_motor"])

    steering_motor = MotorController(MOTORS["small_motor"])
    steering = ContinuousSteeringController(
        motor=steering_motor,
        esp32=esp32,
        initial_angle=150.0,
        gear_ratio=1.5,
    )
    steering.start()

    gps = SerialGPSReader()
    redis_client = RedisManager(REDIS_HOST, 6379)

    replayer = TrajectoryReplayer(
        filepath="recorded_drive.json",
        motor_controller=motor,
        steering_controller=steering,
        gps_reader=gps,
        redis_client=redis_client,
        bike_id=BIKE_ID,
    )

    try:
        replayer.play()
    except KeyboardInterrupt:
        print("❌ Ctrl+C detected! Stopping the bike...")
        motor.stop_immediately()
        steering.stop()

#!/usr/bin/env python3
import time
import threading
from evdev import InputDevice, ecodes
from select import select


class GamepadController:
    """Handles gamepad input and event processing."""

    AXIS_CODES = {
        1: "LY",  # Left stick Y-axis => big motor
        2: "RX",  # Right stick X-axis => steering
    }

    def __init__(self, device_path="/dev/input/event4"):
        self.device_path = device_path
        self.gamepad = None
        self.axis_state = {"LY": 0.0, "RX": 0.0}
        self.running = False
        self.input_thread = None
        self.callbacks = {"LY": [], "RX": []}

    def connect(self):
        """Connect to the gamepad device."""
        try:
            self.gamepad = InputDevice(self.device_path)
            print(f"🎮 Connected to {self.gamepad.name} on {self.device_path}")
            return True
        except Exception as e:
            print(f"Failed to connect to gamepad: {e}")
            return False

    def normalize_axis(self, axis_code, value):
        """Normalize axis values to a -1.0 to 1.0 range."""
        if axis_code == 1:  # LY
            return round((32767.5 - value) / 32767.5, 3)
        elif axis_code == 2:  # RX
            return round((value - 32767.5) / 32767.5, 3)
        return 0.0

    def register_callback(self, axis_name, callback_function):
        """Register a callback function for an axis."""
        if axis_name in self.callbacks:
            self.callbacks[axis_name].append(callback_function)

    def process_controller_inputs(self):
        """Process inputs from the gamepad."""
        while self.running:
            r, _, _ = select([self.gamepad.fd], [], [], 0.01)
            if r:
                for event in self.gamepad.read():
                    if event.type == ecodes.EV_ABS:
                        code = event.code
                        axis_name = self.AXIS_CODES.get(code)
                        if axis_name:
                            new_val = self.normalize_axis(code, event.value)
                            old_val = self.axis_state[axis_name]
                            if abs(new_val - old_val) > 0.1:  # Sensitivity threshold
                                self.axis_state[axis_name] = new_val
                                # Execute all callbacks for this axis
                                for callback in self.callbacks[axis_name]:
                                    callback(new_val)
            time.sleep(0.01)

    def start(self):
        """Start the gamepad input processing thread."""
        if not self.gamepad:
            if not self.connect():
                return False

        self.running = True
        self.input_thread = threading.Thread(
            target=self.process_controller_inputs, daemon=True
        )
        self.input_thread.start()
        return True

    def stop(self):
        """Stop the gamepad input processing thread."""
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)


class DriveController:
    """Controls the main drive motor."""

    def __init__(self, motor_controller, max_pwm=70):
        self.motor = motor_controller
        self.max_pwm = max_pwm
        self.current_value = 0.0

    def handle_drive_input(self, value):
        """Handle drive input from the gamepad."""
        deadzone = 0.1

        # # Check if sign has changed (direction reversal)
        # sign_changed = (self.current_value > 0 and value < 0) or (
        #     self.current_value < 0 and value > 0
        # )

        # Handle deadzone
        if abs(value) < deadzone:
            self.motor.stop_immediately()
            print("Drive motor STOP!")
            self.current_value = value
            return

        # Handle direction change with a short pause
        # if sign_changed and abs(self.current_value) > deadzone:
        #     self.short_stop_transition()

        # Set motor speed
        pwm = int(min(abs(value), 1.0) * self.max_pwm)

        if value > 0:
            print(f"Forward {pwm}%")
            self.motor.motor_control("forward", speed=pwm)
        else:
            print(f"Reverse {pwm}%")
            self.motor.motor_control("reverse", speed=pwm)

        # Update current value
        self.current_value = value

    # def short_stop_transition(self):
    #     """
    #     Stop the motor briefly when changing direction.
    #     """
    #     print("⚠️ Direction change detected: Stopping motor briefly...")
    #     self.motor.graceful_stop()
    #     time.sleep(0.5)  # Short pause

    def stop(self):
        """Stop the drive motor."""
        self.motor.stop_immediately()
        self.current_value = 0.0


class SteeringController:
    """Controls the steering mechanism."""

    def __init__(self, continuous_controller, center_angle=150.0, max_angle_delta=60):
        self.steering_controller = continuous_controller
        self.center_angle = center_angle
        self.max_angle_delta = max_angle_delta

    def handle_steering_input(self, value):
        """Handle steering input from the gamepad."""
        deadzone = 0.1

        if abs(value) < deadzone:
            target_angle = self.center_angle
        else:
            target_angle = self.center_angle + (value * self.max_angle_delta)

        print(f"Steering target => {target_angle:.1f}° (from joystick {value:.2f})")
        self.steering_controller.set_target_angle(target_angle)

    def center_steering(self):
        """Center the steering."""
        self.steering_controller.set_target_angle(self.center_angle)

    def stop(self):
        """Stop the steering controller."""
        self.steering_controller.stop()


class RCCarController:
    """Main controller class for the RC car."""

    def __init__(self):
        # Existing setup...
        from Motor.motor import MotorController
        from Motor.config import MOTORS
        from Motor.ESP32.main import ESP32SerialReader
        from BLT.continuous_steering import ContinuousSteeringController

        # GPS + Redis
        from Redis.redis_manager import RedisManager
        from GPS.GPS_reader import SerialGPSReader
        from server.config.server_config import BIKE_ID, REDIS_HOST

        self.redis = RedisManager(REDIS_HOST, 6379)
        self.gps_reader = SerialGPSReader()
        self.bike_id = BIKE_ID

        # Motors
        self.big_motor = MotorController(MOTORS["big_motor"])
        self.drive_controller = DriveController(self.big_motor)

        self.esp32 = ESP32SerialReader()
        self.steering_motor = MotorController(MOTORS["small_motor"])
        self.continuous_steering = ContinuousSteeringController(
            motor=self.steering_motor,
            esp32=self.esp32,
            initial_angle=150.0,
            gear_ratio=1.5,
        )
        self.steering_controller = SteeringController(self.continuous_steering)

        # Gamepad
        self.gamepad = GamepadController()

    def initialize(self):
        """Initialize all components."""
        self.esp32.connect()
        self.continuous_steering.start()

        # Start GPS loop
        self.start_gps_thread()

        if not self.gamepad.connect():
            return False

        self.gamepad.register_callback("LY", self.drive_controller.handle_drive_input)
        self.gamepad.register_callback(
            "RX", self.steering_controller.handle_steering_input
        )

        return True

    def start(self):
        """Start the RC car controller."""
        if not self.initialize():
            print("Failed to initialize components.")
            return False

        # Start gamepad input processing
        self.gamepad.start()
        print("RC Car Controller started. Press Ctrl+C to exit.")
        return True

    def stop(self):
        """Stop all components."""
        print("Shutting down RC Car Controller...")
        self.gamepad.stop()
        self.drive_controller.stop()
        self.steering_controller.stop()
        self.steering_motor.cleanup()
        self.esp32.close()
        print("Shutdown complete.")

    def start_gps_thread(self):
        """Starts the background thread to send GPS data every second."""

        def gps_loop():
            while True:
                data = self.gps_reader.read_data()
                if data:
                    payload = {
                        "bike_id": self.bike_id,
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timestamp": time.time(),
                    }
                    self.redis.push_gps_data(self.bike_id, payload)
                time.sleep(1)

        gps_thread = threading.Thread(target=gps_loop, daemon=True)
        gps_thread.start()


def main():
    """Main entry point."""
    rc_car = RCCarController()

    try:
        if rc_car.start():
            # Keep the main thread alive
            while True:
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        rc_car.stop()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import time
import threading
from evdev import InputDevice, ecodes
from select import select
import json


class GamepadController:
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
        try:
            self.gamepad = InputDevice(self.device_path)
            print(f"🎮 Connected to {self.gamepad.name} on {self.device_path}")
            return True
        except Exception as e:
            print(f"Failed to connect to gamepad: {e}")
            return False

    def normalize_axis(self, axis_code, value):
        if axis_code == 1:  # LY
            return round((32767.5 - value) / 32767.5, 3)
        elif axis_code == 2:  # RX
            return round((value - 32767.5) / 32767.5, 3)
        return 0.0

    def register_callback(self, axis_name, callback_function):
        if axis_name in self.callbacks:
            self.callbacks[axis_name].append(callback_function)

    def process_controller_inputs(self):
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
                            if abs(new_val - old_val) > 0.1:
                                self.axis_state[axis_name] = new_val
                                for callback in self.callbacks[axis_name]:
                                    callback(new_val)
            time.sleep(0.01)

    def start(self):
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
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)


class DriveController:
    def __init__(self, motor_controller, max_pwm=70):
        self.motor = motor_controller
        self.max_pwm = max_pwm
        self.current_value = 0.0
        self.latest_throttle = 0.0

    def handle_drive_input(self, value):
        deadzone = 0.1
        if abs(value) < deadzone:
            self.motor.stop_immediately()
            self.current_value = 0.0
            self.latest_throttle = 0.0
            print("Drive motor STOP!")
            return

        pwm = int(min(abs(value), 1.0) * self.max_pwm)
        if value > 0:
            self.motor.motor_control("forward", speed=pwm)
        else:
            self.motor.motor_control("reverse", speed=pwm)

        self.current_value = value
        self.latest_throttle = value

    def stop(self):
        self.motor.stop_immediately()
        self.current_value = 0.0
        self.latest_throttle = 0.0


class SteeringController:
    def __init__(self, continuous_controller, center_angle=150.0, max_angle_delta=60):
        self.steering_controller = continuous_controller
        self.center_angle = center_angle
        self.max_angle_delta = max_angle_delta
        self.latest_steering = 0.0

    def handle_steering_input(self, value):
        deadzone = 0.1
        if abs(value) < deadzone:
            target_angle = self.center_angle
        else:
            target_angle = self.center_angle + (value * self.max_angle_delta)

        self.latest_steering = value
        self.steering_controller.set_target_angle(target_angle)

    def center_steering(self):
        self.steering_controller.set_target_angle(self.center_angle)

    def stop(self):
        self.steering_controller.stop()


class RCCarController:
    def __init__(self):
        from Motor.motor import MotorController
        from Motor.config import MOTORS
        from Motor.ESP32.main import ESP32SerialReader
        from BLT.continuous_steering import ContinuousSteeringController

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

        self.gamepad = GamepadController()
        self.logged_data = []

    def initialize(self):
        self.esp32.connect()
        self.continuous_steering.start()
        self.start_logging_thread()

        if not self.gamepad.connect():
            return False

        self.gamepad.register_callback("LY", self.drive_controller.handle_drive_input)
        self.gamepad.register_callback(
            "RX", self.steering_controller.handle_steering_input
        )
        return True

    def start(self):
        if not self.initialize():
            print("Failed to initialize components.")
            return False
        self.gamepad.start()
        print("RC Car Controller started. Press Ctrl+C to exit.")
        return True

    def stop(self):
        print("Shutting down RC Car Controller...")
        self.gamepad.stop()
        self.drive_controller.stop()
        self.steering_controller.stop()
        self.steering_motor.cleanup()
        self.esp32.close()
        self.save_log()
        print("Shutdown complete.")

    def start_logging_thread(self):
        def log_loop():
            while True:
                angle = self.esp32.request_data()
                if angle is not None:
                    self.logged_data.append(
                        {
                            "timestamp": time.time(),
                            "heading_angle": angle,
                            "joystick": {
                                "throttle": self.drive_controller.latest_throttle,
                                "steering": self.steering_controller.latest_steering,
                            },
                        }
                    )
                time.sleep(0.8)

        threading.Thread(target=log_loop, daemon=True).start()

    def save_log(self, filename="recorded_drive.json"):
        with open(filename, "w") as f:
            json.dump(self.logged_data, f, indent=2)


def main():
    rc_car = RCCarController()
    try:
        if rc_car.start():
            while True:
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        rc_car.stop()


if __name__ == "__main__":
    main()

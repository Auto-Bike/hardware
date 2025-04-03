#!/usr/bin/env python3
import time
import threading
from evdev import InputDevice, ecodes
from select import select

# Big motor for forward/back
from Motor.motor import MotorController
from Motor.config import MOTORS

# For the continuous steering approach
from Motor.ESP32.main import ESP32SerialReader
from BLT.continuous_steering import ContinuousSteeringController

# ---- Setup big motor pins, etc. ----
big_motor = MotorController(MOTORS["big_motor"])

# ---- Setup small steering motor with the new continuous approach ----
esp32 = ESP32SerialReader()
esp32.connect()
steering_motor = MotorController(
    MOTORS["small_motor"]
)  # pins for the small steering motor
steering_controller = ContinuousSteeringController(
    motor=steering_motor,
    esp32=esp32,
    initial_angle=150.0,  # center
    gear_ratio=1.5,
)
steering_controller.start()  # start the background PID loop

# ---- Setup gamepad device ----
DEVICE_PATH = "/dev/input/event4"
gamepad = InputDevice(DEVICE_PATH)
print(f"🎮 Connected to {gamepad.name} on {DEVICE_PATH}")

AXIS_CODES = {
    1: "LY",  # Left stick Y-axis => big motor
    2: "RX",  # (LT) => steering x
}

# For storing the current axis values
axis_state = {"LY": 0.0, "RX": 0.0}
running = True


def normalize_axis(axis_code, value):
    # Same logic as before
    if axis_code == 1:  # LY
        return round((32767.5 - value) / 32767.5, 3)
    elif axis_code == 2:  # RX
        return round((value - 32767.5) / 32767.5, 3)
    return 0.0


MAX_BIG_MOTOR_PWM = 70
STEERING_CENTER = 150.0
STEERING_MAX = 60  # ±60° from center


def short_stop_transition():
    """
    Stop or gently ramp the motor for a brief period,
    allowing mechanical inertia to settle before reversing.
    """
    print("⚠️ Sign change detected: Stopping motor briefly...")
    big_motor.graceful_stop()  # Or graceful_stop()
    time.sleep(0.5)  # short pause


def handle_left_stick_y(value):
    """
    Big motor forward/back with short stop if sign changes.
    """
    global axis_state  # or pass old_value in as a parameter

    deadzone = 0.1
    # old_value = axis_state["LY"]  # The last stored joystick value

    # No need to detect the sign changed, assume it can handle pretty well
    # # Check if sign has changed (e.g. from + to - or - to +)
    # sign_changed = (old_value > 0 and value < 0) or (old_value < 0 and value > 0)

    # # If the user let go or reversed direction, do a short stop
    # # i wasnt sure if this was needed  but just until testing is done
    # if sign_changed:
    #     short_stop_transition()

    # After short stop, handle deadzone
    if abs(value) < deadzone:
        big_motor.stop_immediately()
        print("Big motor STOP!")
        axis_state["LY"] = value
        # time.sleep(0.05)  # short pause
        return

    pwm = int(min(abs(value), 1.0) * MAX_BIG_MOTOR_PWM)

    if value > 0:
        print(f"Forward {pwm}%")
        big_motor.motor_control("forward", speed=pwm)
    else:
        print(f"Reverse {pwm}%")
        big_motor.motor_control("reverse", speed=pwm)

    # Finally, update the stored axis value
    axis_state["LY"] = value


def handle_right_stick_x(value):
    """
    Continuous steering: set a new target angle for the PID.
    """
    deadzone = 0.1
    if abs(value) < deadzone:
        target_angle = STEERING_CENTER
    else:
        target_angle = STEERING_CENTER + (value * STEERING_MAX)

    print(f"Steering target => {target_angle:.1f}° (from joystick {value:.2f})")
    steering_controller.set_target_angle(target_angle)


def process_controller_inputs():
    global running
    while running:
        r, _, _ = select([gamepad.fd], [], [], 0.01)
        if r:
            for event in gamepad.read():
                if event.type == ecodes.EV_ABS:
                    code = event.code
                    axis_name = AXIS_CODES.get(code)
                    if axis_name:
                        new_val = normalize_axis(code, event.value)
                        old_val = axis_state[axis_name]
                        if abs(new_val - old_val) > 0.1:  # sensitivity of the sticker
                            axis_state[axis_name] = new_val
                            if axis_name == "LY":
                                handle_left_stick_y(new_val)
                            elif axis_name == "RX":
                                handle_right_stick_x(new_val)
        time.sleep(0.01)


def main():
    global running
    input_thread = threading.Thread(target=process_controller_inputs, daemon=True)
    input_thread.start()

    print("Controller started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        running = False
        input_thread.join()
        # Stop everything
        big_motor.stop_immediately()
        steering_controller.stop()  # This stops the continuous PID thread
        steering_motor.cleanup()  # Cleanup GPIO
        esp32.close()


if __name__ == "__main__":
    main()

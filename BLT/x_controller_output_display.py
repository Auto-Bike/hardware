#!/usr/bin/env python3
from evdev import InputDevice, ecodes
from select import select
import time
import threading

# ======================
# Controller Configuration
# ======================

DEVICE_PATH = "/dev/input/event4"  # Adjust this to your controller's path

try:
    gamepad = InputDevice(DEVICE_PATH)
    print(f"🎮 Connected to {gamepad.name} on {DEVICE_PATH}")
except FileNotFoundError:
    print(f"❌ Controller not found at {DEVICE_PATH}")
    print("Try running 'ls -la /dev/input/event*' to find available devices")
    exit(1)

# Only tracking LY (Left Stick Y-axis) and LT (Left Trigger, repurposed as RS-X)
AXIS_CODES = {
    1: "LY",  # Left stick Y-axis
    2: "LT",  # Left trigger (used as right stick X for steering)
}

# ======================
# Global State and Thread Lock
# ======================

axis_state = {"LY": 0.0, "LT": 0.0}
state_lock = threading.Lock()
running = True  # Global flag for stopping the program

# ======================
# Normalization Functions
# ======================


def normalize_axis(code, value):
    """
    Normalize axis values from raw input range to -1.0 to 1.0.

    For LT (code 2): Converts raw value (0-65535) so that center (32767.5) maps to 0,
    values lower than center become negative and higher become positive.

    For LY (code 1): Flips the axis so that up is positive and down is negative.
    """
    if code == 2:  # LT (used as RS-X for steering)
        normalized = (value - 32767.5) / 32767.5
        return round(normalized, 3)
    elif code == 1:  # LY (Left Stick Y)
        normalized = (32767.5 - value) / 32767.5
        return round(normalized, 3)
    return 0.0


# ======================
# Action Handling Functions
# ======================


def handle_left_stick_y(value):
    """
    Handle left stick Y-axis movement.

    Range: -1.0 (down) to 1.0 (up)
    Positive values move forward; negative values move backward.
    PWM output is capped at 70% to protect the motor.
    """
    MAX_PWM = 60  # Cap motor power at 70%

    if abs(value) < 0.1:  # Deadzone
        print("Bike Stop! PWM = 0%")
        # stop_motor_pwm()
        return

    # Scale value to a PWM range of 0 to MAX_PWM
    pwm = int(min(abs(value), 1.0) * MAX_PWM)

    if value > 0:
        print(f"LY up ({value:.3f}): Move forward with {pwm}% PWM")
        # set_motor_pwm_forward(pwm)
    else:
        print(f"LY down ({value:.3f}): Move backward with {pwm}% PWM")
        # set_motor_pwm_backward(pwm)


def handle_right_stick_x(value):
    """
    Handle right stick X-axis input (repurposed from LT for steering).

    Range: -1.0 (left) to 1.0 (right), mapping to a steering angle with a maximum of 60°.
    """
    max_angle = 60  # Maximum steering angle in degrees

    if abs(value) < 0.1:  # Deadzone
        print(f"RS-X neutral ({value:.3f}): Steering angle = 0°")
        # set_steering_angle(0)
        return

    angle = int(value * max_angle)
    if value > 0:
        print(f"RS-X right ({value:.3f}): Turn right at {angle}°")
        # set_steering_angle(angle)
    else:
        print(f"RS-X left ({value:.3f}): Turn left at {abs(angle)}°")
        # set_steering_angle(angle)


# ======================
# Input Processing Thread
# ======================


def process_controller_inputs():
    """
    Process controller inputs in a separate thread.
    Reads from the controller and triggers action handlers on significant changes.
    """
    global running
    while running:
        # Non-blocking check for new input events
        r, _, _ = select([gamepad.fd], [], [], 0.01)
        if r:
            for event in gamepad.read():
                if event.type == ecodes.EV_ABS:
                    code = event.code
                    axis = AXIS_CODES.get(code)
                    if axis:
                        new_value = normalize_axis(code, event.value)
                        with state_lock:
                            old_value = axis_state[axis]
                            if abs(new_value - old_value) > 0.01:
                                axis_state[axis] = new_value
                                if axis == "LY":
                                    handle_left_stick_y(new_value)
                                elif axis == "LT":
                                    handle_right_stick_x(new_value)
        time.sleep(0.01)


# ======================
# Main Program Loop
# ======================


def main():
    """
    Main program that starts the input processing thread and maintains the main loop.
    """
    global running
    try:
        input_thread = threading.Thread(target=process_controller_inputs)
        input_thread.daemon = True
        input_thread.start()

        print("Controller action handler started. Press Ctrl+C to exit.")
        print("Monitoring LY (Left Stick Y) and LT (used as RS-X for steering)...")

        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    finally:
        running = False
        input_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()

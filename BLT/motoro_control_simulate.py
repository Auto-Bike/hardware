#!/usr/bin/env python3
from evdev import InputDevice, ecodes
from select import select
import time
import threading

# ======================
# Controller Configuration
# ======================

DEVICE_PATH = "/dev/input/event4"  # Adjust to your actual controller path

try:
    gamepad = InputDevice(DEVICE_PATH)
    print(f"🎮 Connected to {gamepad.name} on {DEVICE_PATH}")
except FileNotFoundError:
    print(f"❌ Controller not found at {DEVICE_PATH}")
    print("Try running 'ls -la /dev/input/event*' to find available devices")
    exit(1)

# We only track LY (Left Stick Y) and LT (Left Trigger).
AXIS_CODES = {
    1: "LY",  # Left stick Y-axis
    2: "LT",  # Left trigger (repurposed for steering)
}

# ======================
# Global State
# ======================
axis_state = {"LY": 0.0, "LT": 0.0}
state_lock = threading.Lock()
running = True


# ======================
# Normalization Function
# ======================
def normalize_axis(code, value):
    """
    Convert raw axis values (0..65535) to -1.0..+1.0.

    For LT (code 2): center ~32767 => 0.0
    For LY (code 1): 0 => +1.0 (up), 65535 => -1.0 (down)
    """
    midpoint = 32767.5

    if code == 2:  # LT axis
        #  0 => -1.0, 65535 => +1.0
        return round((value - midpoint) / midpoint, 3)
    elif code == 1:  # LY axis
        #  0 => +1.0, 65535 => -1.0
        return round((midpoint - value) / midpoint, 3)
    return 0.0


# ======================
# Action Handling
# ======================
def short_stop_transition():
    """
    Stop or gently ramp the motor for a brief period,
    allowing mechanical inertia to settle before reversing.
    """
    print("⚠️ Sign change detected: Stopping motor briefly...")
    # big_motor.graceful_stop()  # Or graceful_stop()
    time.sleep(0.5)  # short pause


def handle_left_stick_y(value):
    """
    Fake “big motor” control: just print output.
    """
    global axis_state  # or pass old_value in as a parameter
    MAX_PWM = 60  # limit power to 60%
    deadzone = 0.1
    old_value = axis_state["LY"]  # The last stored joystick value

    # Check if sign has changed (e.g. from + to - or - to +)
    sign_changed = (old_value > 0 and value < 0) or (old_value < 0 and value > 0)

    # If the user let go or reversed direction, do a short stop
    if sign_changed:
        short_stop_transition()

    if abs(value) < deadzone:
        print("Bike Stop! PWM = 0%")
        return

    pwm = int(min(abs(value), 1.0) * MAX_PWM)

    if value > 0:
        print(f"LY up ({value:.3f}): Move forward with {pwm}% PWM")
    else:
        print(f"LY down ({value:.3f}): Move backward with {pwm}% PWM")


def handle_right_stick_x(value):
    """
    Fake “small motor” steering: just print output.
    """
    max_angle = 60  # ±60°
    deadzone = 0.1

    if abs(value) < deadzone:
        print(f"RS-X neutral ({value:.3f}): Steering angle = 0°")
        return

    angle = int(value * max_angle)
    if value > 0:
        print(f"RS-X right ({value:.3f}): Turn right at {angle}°")
    else:
        print(f"RS-X left ({value:.3f}): Turn left at {abs(angle)}°")


# We'll reuse the “LT” axis for steering:
def dispatch_axis(axis_name, new_value):
    if axis_name == "LY":
        handle_left_stick_y(new_value)
    elif axis_name == "LT":
        handle_right_stick_x(new_value)


# ======================
# Input Processing Thread
# ======================
def process_controller_inputs():
    global running
    while running:
        # Non-blocking check for controller events
        r, _, _ = select([gamepad.fd], [], [], 0.01)
        if r:
            for event in gamepad.read():
                if event.type == ecodes.EV_ABS:
                    code = event.code
                    axis_name = AXIS_CODES.get(code)
                    if axis_name:
                        new_val = normalize_axis(code, event.value)
                        with state_lock:
                            old_val = axis_state[axis_name]
                            if abs(new_val - old_val) > 0.1:  # significant change
                                axis_state[axis_name] = new_val
                                dispatch_axis(axis_name, new_val)
        time.sleep(0.01)


# ======================
# Main Program
# ======================
def main():
    global running
    try:
        input_thread = threading.Thread(target=process_controller_inputs, daemon=True)
        input_thread.start()
        print("Controller action handler started. Press Ctrl+C to exit.")

        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    finally:
        running = False
        input_thread.join(timeout=1.0)


if __name__ == "__main__":
    main()

from evdev import InputDevice, ecodes
from select import select
import os
import time

# Controller configuration
device_path = "/dev/input/event4"
gamepad = InputDevice(device_path)

# Axis mapping
axis_labels = {
    0: "LX",
    1: "LY",
    2: "LT",
    3: "RX",
    4: "RY",
    5: "RT",
    16: "DPad-X",
    17: "DPad-Y",
}

# Initialize axis state
axis_state = {label: 0 for label in axis_labels.values()}

# Track last activity time for each axis
last_activity = {label: 0 for label in axis_labels.values()}
RESET_TIMEOUT = 2.0  # Seconds of inactivity before resetting to 0


def normalize_axis(code, value):
    """Normalize axis values to a consistent range"""
    if code in [2, 5]:  # Triggers
        normalized = (value - 32767.5) / 32767.5
        return round(normalized, 3)
    elif code in [0, 1, 3, 4]:  # Analog sticks
        normalized = (32767.5 - value) / 32767.5
        return round(normalized, 3)
    elif code in [16, 17]:  # D-Pad
        return value
    return value


def check_for_resets():
    """Reset axes to 0 if inactive for RESET_TIMEOUT seconds"""
    current_time = time.time()
    for label in axis_state:
        if current_time - last_activity[label] > RESET_TIMEOUT:
            # Only reset non-zero values to avoid unnecessary updates
            if axis_state[label] != 0:
                axis_state[label] = 0


def display_state():
    """Display the current state of all controller axes"""
    os.system("clear" if os.name == "posix" else "cls")
    print("🎮 Xbox Controller Input Monitor (normalized) — CTRL+C to quit\n")

    # Display in rows of 4 for better readability
    labels = list(axis_state.keys())
    for i in range(0, len(labels), 4):
        row_labels = labels[i : i + 4]
        for label in row_labels:
            # Color coding: blue for active, white for idle
            if axis_state[label] != 0:
                value_str = f"\033[94m{axis_state[label]:>6.3f}\033[0m"  # Blue text
            else:
                value_str = f"{axis_state[label]:>6.3f}"  # Default color
            print(f"{label:>5}: {value_str}", end=" | ")
        print()

    print("\nInactive axes will reset to 0 after 2 seconds of no input")


print("🎮 Xbox Controller Input Monitor (Press Ctrl+C to exit)\n")

try:
    while True:
        # Check for new events (non-blocking)
        r, _, _ = select([gamepad], [], [], 0.01)
        if r:
            for event in gamepad.read():
                if event.type == ecodes.EV_ABS:
                    label = axis_labels.get(event.code)
                    if label:
                        new_value = normalize_axis(event.code, event.value)
                        # Only update if value actually changed
                        if new_value != axis_state[label]:
                            axis_state[label] = new_value
                            last_activity[label] = time.time()

        # Check if any axes should be reset
        check_for_resets()

        # Update display
        display_state()

        # Small delay to prevent excessive CPU usage
        time.sleep(0.03)

except KeyboardInterrupt:
    print("\n👋 Exiting...")
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    # Reset terminal colors if needed
    print("\033[0m", end="")

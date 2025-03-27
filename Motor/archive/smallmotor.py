from config import MOTORS
from motor import MotorController

# Load small motor configuration
small_motor = MotorController(MOTORS["small_motor"])

try:
    print("Press Ctrl+C to exit.")
    while True:
        command = input("Enter command (right/left/stop): ").strip().lower()
        if command in ["right", "left"]:
            time = float(input("Enter stop time (0 to 2): "))
            if 0 <= time <= 2.0:
                small_motor.motor_control(command, time_duration = time)
            else:
                print("Time must be between 0 and 10.")
        elif command == "stop":
            small_motor.stop_immediately()
        else:
            print("Invalid command.")

except KeyboardInterrupt:
    small_motor.cleanup()
    print("\nExiting program.")

finally:
    small_motor.cleanup()

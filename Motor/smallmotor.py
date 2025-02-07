from motor import MotorController
from config import MOTORS

# Load small motor configuration
small_motor = MotorController(MOTORS["small_motor"])

try:
    print("Press Ctrl+C to exit.")
    while True:
        command = input("Enter command (forward/reverse/stop): ").strip().lower()
        if command in ["forward", "reverse"]:
            speed = int(input("Enter speed (0 to 100): "))
            if 0 <= speed <= 100:
                small_motor.motor_control(command, speed)
            else:
                print("Speed must be between 0 and 100.")
        elif command == "stop":
            small_motor.motor_control("stop", 0)
        else:
            print("Invalid command.")

except KeyboardInterrupt:
    print("\nExiting program.")

finally:
    small_motor.cleanup()

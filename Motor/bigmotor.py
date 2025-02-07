from motor import MotorController
from config import MOTORS

# Load big motor configuration
big_motor = MotorController(MOTORS["big_motor"])

try:
    print("Press Ctrl+C to exit.")
    while True:
        command = input("Enter command (forward/reverse/stop): ").strip().lower()
        if command in ["forward", "reverse"]:
            speed = int(input("Enter speed (0 to 100): "))
            if 0 <= speed <= 100:
                big_motor.motor_control(command, speed)
            else:
                print("Speed must be between 0 and 100.")
        elif command == "stop":
            big_motor.motor_control("stop", 0)
        else:
            print("Invalid command.")

except KeyboardInterrupt:
    print("\nExiting program.")

finally:
    big_motor.cleanup()

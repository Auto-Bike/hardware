import RPi.GPIO as GPIO
import time

# Define GPIO pins for motor control
RPWM_PIN = 18  # Pin 12, PWM0
LPWM_PIN = 19  # Pin 35, PWM1
R_EN_PIN = 23  # Pin 16
L_EN_PIN = 24  # Pin 18

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)  # Use Broadcom pin numbering
GPIO.setup(RPWM_PIN, GPIO.OUT)
GPIO.setup(LPWM_PIN, GPIO.OUT)
GPIO.setup(R_EN_PIN, GPIO.OUT)
GPIO.setup(L_EN_PIN, GPIO.OUT)

# Set up PWM on the RPWM and LPWM pins
RIGHT_PWM = GPIO.PWM(RPWM_PIN, 1000)  # 1 kHz frequency
LEFT_PWM = GPIO.PWM(LPWM_PIN, 1000)   # 1 kHz frequency

# Start with 0% duty cycle (off)
RIGHT_PWM.start(0)
LEFT_PWM.start(0)

def motor_control(direction, speed):
    """
    Controls the motor direction and speed.
    :param direction: 'forward', 'reverse', or 'stop'
    :param speed: Speed as a percentage (0 to 100)
    """
    if direction == "forward":
        GPIO.output(R_EN_PIN, GPIO.HIGH)
        GPIO.output(L_EN_PIN, GPIO.HIGH)
        RIGHT_PWM.ChangeDutyCycle(speed)
        LEFT_PWM.ChangeDutyCycle(0)
    elif direction == "reverse":
        GPIO.output(R_EN_PIN, GPIO.HIGH)
        GPIO.output(L_EN_PIN, GPIO.HIGH)
        RIGHT_PWM.ChangeDutyCycle(0)
        LEFT_PWM.ChangeDutyCycle(speed)
    elif direction == "stop":
        GPIO.output(R_EN_PIN, GPIO.LOW)
        GPIO.output(L_EN_PIN, GPIO.LOW)
        RIGHT_PWM.ChangeDutyCycle(0)
        LEFT_PWM.ChangeDutyCycle(0)
    else:
        print("Invalid direction! Use 'forward', 'reverse', or 'stop'.")

try:
    print("Press Ctrl+C to exit.")
    while True:
        command = input("Enter command (forward/reverse/stop): ").strip().lower()
        if command in ["forward", "reverse"]:
            speed = int(input("Enter speed (0 to 100): "))
            if 0 <= speed <= 100:
                motor_control(command, speed)
            else:
                print("Speed must be between 0 and 100.")
        elif command == "stop":
            motor_control("stop", 0)
        else:
            print("Invalid command.")

except KeyboardInterrupt:
    print("\nExiting program.")

finally:
    # Clean up GPIO settings
    RIGHT_PWM.stop()
    LEFT_PWM.stop()
    GPIO.cleanup()

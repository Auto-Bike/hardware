import logging
import time
from enum import Enum

import RPi.GPIO as GPIO

logging.basicConfig(level=logging.INFO)


class SteeringSpeed(Enum):
    """Enum for steering speed levels."""

    Regular = 30
    LOW = 30
    MEDIUM = 50
    HIGH = 70


class MotorController:
    """Class to control a motor using PWM and GPIO."""

    def __init__(self, motor_pins, pwm_freq=1000):
        """
        Initializes the motor controller with the given GPIO pin configuration.
        :param motor_pins: Dictionary containing 'rpwm', 'lpwm', 'r_en', 'l_en'
        :param pwm_freq: PWM frequency (default 1000Hz)
        """
        self.rpwm_pin = motor_pins["rpwm"]
        self.lpwm_pin = motor_pins["lpwm"]
        self.r_en_pin = motor_pins["r_en"]
        self.l_en_pin = motor_pins["l_en"]

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.rpwm_pin, GPIO.OUT)
        GPIO.setup(self.lpwm_pin, GPIO.OUT)
        GPIO.setup(self.r_en_pin, GPIO.OUT)
        GPIO.setup(self.l_en_pin, GPIO.OUT)

        # Setup PWM
        self.right_pwm = GPIO.PWM(self.rpwm_pin, pwm_freq)
        self.left_pwm = GPIO.PWM(self.lpwm_pin, pwm_freq)

        # Start PWM with 0% duty cycle (off)
        self.right_pwm.start(0)
        self.left_pwm.start(0)

        # Track current state
        self.current_direction = "stop"
        self.current_speed = 0

    def motor_control(self, direction, speed=None, time_duration:float=None):
        """
        Controls the motor direction and speed.
        :param direction: 'forward', 'reverse', or 'stop'
        :param speed: Speed as a percentage (0 to 100)
        """
        if direction == "forward":
            # Update state for forward
            self.current_direction = "forward"
            self.current_speed = speed
            GPIO.output(self.r_en_pin, GPIO.HIGH)
            GPIO.output(self.l_en_pin, GPIO.HIGH)
            self.right_pwm.ChangeDutyCycle(speed)
            self.left_pwm.ChangeDutyCycle(0)
            logging.info(f"Motor running FORWARD at {speed}% speed")
        elif direction == "reverse":
            # Update state for reverse
            self.current_direction = "reverse"
            self.current_speed = speed
            GPIO.output(self.r_en_pin, GPIO.HIGH)
            GPIO.output(self.l_en_pin, GPIO.HIGH)
            self.right_pwm.ChangeDutyCycle(0)
            self.left_pwm.ChangeDutyCycle(speed)
            logging.info(f"Motor running REVERSE at {speed}% speed")
            
        elif direction == "right":
            # Update state for right
            speed = SteeringSpeed.Regular.value
            GPIO.output(self.r_en_pin, GPIO.HIGH)
            GPIO.output(self.l_en_pin, GPIO.HIGH)
            self.right_pwm.ChangeDutyCycle(0)
            self.left_pwm.ChangeDutyCycle(speed)
            logging.info(f"Motor turning RIGHT at {speed}% speed")
            time.sleep(time_duration)
            self.stop_immediately()
            logging.info(f"Motor Stop for {time_duration} seconds")
            
        elif direction == "left":
            # Update state for left
            speed = SteeringSpeed.Regular.value
            GPIO.output(self.r_en_pin, GPIO.HIGH)
            GPIO.output(self.l_en_pin, GPIO.HIGH)
            self.right_pwm.ChangeDutyCycle(0)
            self.left_pwm.ChangeDutyCycle(speed)
            logging.info(f"Motor running LEFT at {speed}% speed")
            time.sleep(time_duration)
            self.stop_immediately()
            logging.info(f"Motor Stop for {time_duration} seconds")

        elif direction == "stop":
            # For stop, do not update the state here.
            # Let graceful_stop handle the deceleration and state update.
            self.graceful_stop()
        else:
            logging.error("Invalid direction! Use 'forward', 'reverse', or 'stop'.")        
            
    def stop_immediately(self):
        """Stops the motor immediately."""
        GPIO.output(self.r_en_pin, GPIO.LOW)
        GPIO.output(self.l_en_pin, GPIO.LOW)
        self.right_pwm.ChangeDutyCycle(0)
        self.left_pwm.ChangeDutyCycle(0)
        self.current_direction = "stop"
        self.current_speed = 0
        logging.info("Motor stopped immediately")

    def graceful_stop(self, step=5, delay=0.2):
        """
        Gradually slows down the motor before stopping completely.

        :param step: Speed reduction step size for each iteration (default 5%)
        :param delay: Time delay between each step in seconds (default 0.2s)
        """
        # If motor is already stopped, exit immediately.
        if self.current_speed == 0:
            logging.info("Motor is already stopped")
            return

        logging.info(f"Gracefully stopping from {self.current_speed}% speed")

        # Store original direction and speed for the deceleration process.
        original_direction = self.current_direction
        original_speed = self.current_speed

        # Gradually reduce speed
        while self.current_speed > 0:
            self.current_speed = max(0, self.current_speed - step)

            if original_direction == "forward":
                self.right_pwm.ChangeDutyCycle(self.current_speed)
            elif original_direction == "reverse":
                self.left_pwm.ChangeDutyCycle(self.current_speed)

            logging.info(f"Reducing speed to {self.current_speed}%")
            time.sleep(delay)

        # Finally, disable the motor completely.
        GPIO.output(self.r_en_pin, GPIO.LOW)
        GPIO.output(self.l_en_pin, GPIO.LOW)
        self.right_pwm.ChangeDutyCycle(0)
        self.left_pwm.ChangeDutyCycle(0)
        self.current_direction = "stop"
        logging.info(
            f"Graceful stop completed: decelerated from {original_speed}% to 0%"
        )

    def cleanup(self):
        """Stops PWM and cleans up GPIO."""
        self.right_pwm.stop()
        self.left_pwm.stop()
        GPIO.cleanup()
        logging.info("GPIO cleanup completed")

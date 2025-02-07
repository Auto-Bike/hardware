import RPi.GPIO as GPIO
import logging

logging.basicConfig(level=logging.INFO)

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

  def motor_control(self, direction, speed):
    """
    Controls the motor direction and speed.
    :param direction: 'forward', 'reverse', or 'stop'
    :param speed: Speed as a percentage (0 to 100)
    """
    if direction == "forward":
      GPIO.output(self.r_en_pin, GPIO.HIGH)
      GPIO.output(self.l_en_pin, GPIO.HIGH)
      self.right_pwm.ChangeDutyCycle(speed)
      self.left_pwm.ChangeDutyCycle(0)
      logging.info(f"Motor running FORWARD at {speed}% speed")
    elif direction == "reverse":
      GPIO.output(self.r_en_pin, GPIO.HIGH)
      GPIO.output(self.l_en_pin, GPIO.HIGH)
      self.right_pwm.ChangeDutyCycle(0)
      self.left_pwm.ChangeDutyCycle(speed)
      logging.info(f"Motor running REVERSE at {speed}% speed")
    elif direction == "stop":
      GPIO.output(self.r_en_pin, GPIO.LOW)
      GPIO.output(self.l_en_pin, GPIO.LOW)
      self.right_pwm.ChangeDutyCycle(0)
      self.left_pwm.ChangeDutyCycle(0)
      logging.info("Motor STOPPED")
    else:
      logging.error("Invalid direction! Use 'forward', 'reverse', or 'stop'.")

  def cleanup(self):
    """Stops PWM and cleans up GPIO."""
    self.right_pwm.stop()
    self.left_pwm.stop()
    GPIO.cleanup()
    logging.info("GPIO cleanup completed")

# continuous_steering.py

import threading
import time
import logging
from Motor.PID.pid_controller import PIDController  # your existing PID class
from Motor.ESP32.main import ESP32SerialReader
from Motor.motor import MotorController

logging.basicConfig(level=logging.INFO)


class ContinuousSteeringController:
    """
    Continuously adjusts a DC motor's steering angle based on a PID loop.
    The angle is read from the ESP32 via your pot/encoder feedback.
    """

    def __init__(
        self,
        motor: MotorController,
        esp32: ESP32SerialReader,
        initial_angle: float = 150.0,
        gear_ratio: float = 1.0,
        kp: float = 0.8,
        ki: float = 0.001,
        kd: float = 0.05,
        output_limits=(-100, 100),
    ):
        """
        :param motor: MotorController instance for the steering DC motor
        :param esp32: ESP32SerialReader instance for reading the current angle
        :param initial_angle: Starting target angle (e.g. 150.0 for center)
        :param gear_ratio: If your motor output ratio differs from the sensor angle
        :param kp, ki, kd: PID gains
        :param output_limits: clamp output to e.g. -100..+100 for PWM
        """
        self.motor = motor
        self.esp32 = esp32
        self.gear_ratio = gear_ratio

        # Create one PID instance, always running
        self.pid = PIDController(
            kp=kp,
            ki=ki,
            kd=kd,
            setpoint=initial_angle,  # degrees
            output_limits=output_limits,
        )

        self._target_angle = initial_angle
        self._stop_flag = False
        self._thread = None

    def start(self):
        """Start the continuous steering thread."""
        if self._thread and self._thread.is_alive():
            logging.warning("Steering thread is already running!")
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logging.info("Continuous Steering Thread started.")

    def stop(self):
        """Stop the continuous steering thread."""
        self._stop_flag = True
        if self._thread:
            self._thread.join(timeout=2.0)
        self.motor.stop_immediately()
        logging.info("Continuous Steering Thread stopped.")

    def set_target_angle(self, angle: float):
        """
        Update the steering setpoint in degrees (e.g. 0..300).
        This can be called anytime (e.g. from the joystick).
        """
        self._target_angle = angle
        self.pid.setpoint = angle
        logging.info(f"New steering target = {angle:.1f}°")

    def _run_loop(self):
        """
        PID loop that continuously runs in the background, driving the motor
        to match the target angle from self._target_angle / self.pid.setpoint.
        """
        min_pwm = 20
        while not self._stop_flag:
            current_angle = self.esp32.request_data()  # e.g. 0..300
            if current_angle is not None:
                # Optionally apply gear ratio if your pot angle differs from actual motor angle
                # pot_angle = current_angle / self.gear_ratio

                control_output = self.pid.compute(current_angle)

                # control_output ~ -100..+100 from the PID
                direction = "left" if control_output > 0 else "right"

                speed = min(100, abs(control_output))
                if 0 < speed < min_pwm:
                    speed = min_pwm

                self.motor.motor_control(direction=direction, speed=speed)

                # If error is small, you could optionally do a partial stop, but usually
                # we let the PID keep it stable. That might require a small Ki for hold.

            time.sleep(0.02)  # 50 Hz update

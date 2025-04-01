import threading
import logging
from Motor.config import MOTORS
from Motor.motor import MotorController
from Motor.ESP32.main import ESP32SerialReader
from Motor.PID.pid_controller import PIDController
from datetime import datetime

# ✅ Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("motor_debug.log"),  # Optional file logging
    ],
)


class SteeringController:
    def __init__(
        self, esp32_reader, motor_controller, target_angle, stop_callback=None
    ):
        self.esp32 = esp32_reader
        self.motor = motor_controller
        self.pid = PIDController(kp=0.8, ki=0.01, kd=0.05, setpoint=target_angle)
        self.stop_callback = stop_callback

    def rotate_to_angle(self, tolerance=2.0, max_time=30, debug=False):
        import time

        timestamps = []
        angles = []
        outputs = []
        setpoints = []

        start_time = time.time()

        while True:
            if self.stop_callback and self.stop_callback():
                logging.warning("⛔ Movement interrupted by stop command.")
                self.motor.stop_immediately()
                break

            current_time = time.time() - start_time
            current_angle = self.esp32.request_data()
            if current_angle is None:
                continue

            control = self.pid.compute(current_angle)

            timestamps.append(current_time)
            angles.append(current_angle)
            outputs.append(control)
            setpoints.append(self.pid.setpoint)

            if abs(self.pid.setpoint - current_angle) <= tolerance:
                self.motor.stop_immediately()
                break

            direction = "left" if control > 0 else "right"
            speed = min(100, abs(control))
            logging.info(
                f"🌀 PID Output: {control:.2f} -> Direction: {direction}, Speed: {speed:.1f}"
            )
            self.motor.motor_control(direction=direction, speed=speed)

            if current_time > max_time:
                logging.warning("⏱️ Timeout reached")
                break

        self.motor.stop_immediately()

        if debug:
            import os
            import matplotlib.pyplot as plt

            os.makedirs("pid_plots", exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_path = f"pid_plots/pid_plot_{timestamp_str}.png"

            plt.figure(figsize=(10, 5))
            plt.plot(timestamps, angles, label="Current Angle")
            plt.plot(timestamps, setpoints, "--", label="Target Angle")
            plt.plot(timestamps, outputs, ":", label="PID Output")
            plt.xlabel("Time (s)")
            plt.ylabel("Angle / Output")
            plt.title("PID Motor Steering Plot")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(plot_path)
            logging.info(f"📊 PID plot saved to: {plot_path}")


class SmallMotorController:
    def __init__(self, neutral_angle: float = 150.0):
        self.motor = MotorController(MOTORS["small_motor"])
        self.esp32 = ESP32SerialReader()
        self.esp32.connect()
        self.neutral_angle = neutral_angle
        self.gear_ratio = 0.6667
        self._stop_requested = False
        self._rotation_thread = None

    def get_current_angle(self):
        angle = self.esp32.request_data()
        if angle is None:
            raise RuntimeError("Unable to read angle from ESP32")
        return angle

    def turn_left_by(self, delta_angle: float):
        current_angle = self.get_current_angle()
        motor_delta = delta_angle / self.gear_ratio
        target_angle = max(0.0, current_angle - motor_delta)
        self._start_rotation_thread(
            target_angle,
            command="left",
            requested_angle=delta_angle,
            current_angle=current_angle,
        )

    def turn_right_by(self, delta_angle: float):
        current_angle = self.get_current_angle()
        motor_delta = delta_angle / self.gear_ratio
        target_angle = min(300.0, current_angle + motor_delta)
        self._start_rotation_thread(
            target_angle,
            command="right",
            requested_angle=delta_angle,
            current_angle=current_angle,
        )

    def turn_to(self, absolute_angle: float):
        current_angle = self.get_current_angle()
        self._start_rotation_thread(
            absolute_angle,
            command="rotate",
            requested_angle=None,
            current_angle=current_angle,
        )

    def center(self):
        current_angle = self.get_current_angle()
        self._start_rotation_thread(
            self.neutral_angle,
            command="center",
            requested_angle=None,
            current_angle=current_angle,
        )

    def _start_rotation_thread(
        self, target_angle, command=None, requested_angle=None, current_angle=None
    ):
        if self._rotation_thread and self._rotation_thread.is_alive():
            logging.warning(
                "⚠️ A rotation is already in progress. Please stop it first."
            )
            return

        self._stop_requested = False
        self._rotation_thread = threading.Thread(
            target=self._rotate_to,
            args=(target_angle, command, requested_angle, current_angle),
        )
        self._rotation_thread.start()

    def _rotate_to(
        self, target_angle, command=None, requested_angle=None, current_angle=None
    ):
        start_angle = self.get_current_angle()
        controller = SteeringController(
            self.esp32,
            self.motor,
            target_angle,
            stop_callback=lambda: self._stop_requested,
        )
        controller.rotate_to_angle()
        new_angle = self.get_current_angle()

        # ✅ Final logs printed AFTER motion finishes
        if command and requested_angle is not None and current_angle is not None:
            logging.info(f"\n➡️ {command.upper()} TURN COMPLETED")
            logging.info(f"🔢 Requested steering angle: {requested_angle:.2f}°")
            logging.info(f"⚙️ Gear ratio: 1 / {self.gear_ratio}")
            logging.info(f"📐 Motor delta: {(requested_angle / self.gear_ratio):.2f}°")
            logging.info(
                f"🎯 Target angle: {target_angle:.2f}° (from {current_angle:.2f}°)"
            )

        logging.info(f"✅ Start angle: {start_angle:.2f}°")
        logging.info(f"✅ Final angle: {new_angle:.2f}°\n")

    def stop(self):
        logging.info("🛑 Stop command received.")
        self._stop_requested = True
        if self._rotation_thread and self._rotation_thread.is_alive():
            self._rotation_thread.join()
            logging.info("✅ Rotation thread stopped.")

    def cleanup(self):
        self.motor.cleanup()
        self.esp32.close()


# 🧪 CLI Interface
if __name__ == "__main__":
    try:
        controller = SmallMotorController()
        logging.info(
            "Commands: left [angle], right [angle], rotate [angle], center, stop"
        )

        while True:
            parts = input("Enter command: ").strip().lower().split()

            if not parts:
                continue

            cmd = parts[0]

            if cmd in ["left", "right", "rotate"] and len(parts) == 2:
                try:
                    angle = float(parts[1])
                    if cmd == "left":
                        controller.turn_left_by(angle)
                    elif cmd == "right":
                        controller.turn_right_by(angle)
                    elif cmd == "rotate":
                        controller.turn_to(angle)
                except ValueError:
                    logging.error("❗ Invalid angle input.")

            elif cmd == "center":
                controller.center()

            elif cmd == "stop":
                controller.stop()

            else:
                logging.warning(
                    "❌ Invalid command. Try: left 30, right 15, rotate 150, center, stop"
                )

    except KeyboardInterrupt:
        logging.info("🛑 Exiting manual control...")

    finally:
        controller.cleanup()

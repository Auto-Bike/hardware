import serial
import time
import threading


class ESP32SerialReader:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.lock = threading.Lock()
        self.last_valid_angle = 150.0  # default center

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"🔌 Connected to ESP32 on {self.port}")
        except serial.SerialException as e:
            print(f"❌ Failed to connect: {e}")
            raise

    def request_data(self):
        with self.lock:
            try:
                message = "r\n"
                self.ser.write(message.encode())
                # print(f"Sent to ESP32: {message.strip()}")  # Optional debug

                response = self.ser.readline().decode("utf-8").strip()
                if response:
                    # print(f"Raw response from ESP32: {response}")  # Optional debug
                    try:
                        adc_value = int(response)
                        angle = self._convert_to_angle(adc_value)

                        if 0 <= angle <= 300:
                            self.last_valid_angle = angle
                            print(f"🎯 Potentiometer angle: {angle:.2f}°")
                            return angle
                        else:
                            print(f"⚠️ Out-of-range angle: {angle:.2f}°")

                    except ValueError:
                        print("⚠️ Invalid numeric response")

                return self.last_valid_angle  # fallback

            except Exception as e:
                print(f"❗ Serial read error: {e}")
                return self.last_valid_angle

    def _convert_to_angle(self, adc_value):
        return (adc_value / 4095.0) * 300.0

    def run_loop(self, interval=1):
        try:
            while True:
                self.request_data()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n🛑 Communication stopped by user.")
        finally:
            self.close()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("🔒 Serial connection closed.")


# If you want to run directly:
if __name__ == "__main__":
    reader = ESP32SerialReader()
    reader.connect()
    reader.run_loop()

# GPS/gps_reader.py

import serial
from typing import Optional


class NMEAParser:
    @staticmethod
    def parse(sentence: str) -> Optional[dict]:
        parts = sentence.split(",")
        if parts[0] == "$GNGGA":
            return {
                "type": "GNGGA",
                "latitude": NMEAParser.convert_latitude(parts[2], parts[3]),
                "longitude": NMEAParser.convert_longitude(parts[4], parts[5]),
            }
        elif parts[0] == "$GNRMC":
            return {
                "type": "GNRMC",
                "latitude": NMEAParser.convert_latitude(parts[3], parts[4]),
                "longitude": NMEAParser.convert_longitude(parts[5], parts[6]),
            }
        return None

    @staticmethod
    def convert_latitude(value: str, direction: str) -> Optional[float]:
        if not value:
            return None
        degrees = float(value[:2])
        minutes = float(value[2:]) / 60
        return round(degrees + minutes, 6) * (-1 if direction == "S" else 1)

    @staticmethod
    def convert_longitude(value: str, direction: str) -> Optional[float]:
        if not value:
            return None
        degrees = float(value[:3])
        minutes = float(value[3:]) / 60
        return round(degrees + minutes, 6) * (-1 if direction == "W" else 1)


class SerialGPSReader:
    def __init__(self, port: str = "/dev/ttyAMA0", baudrate: int = 9600):
        self.serial_connection = serial.Serial(port, baudrate, timeout=1)

    def read_data(self) -> Optional[dict]:
        try:
            line = (
                self.serial_connection.readline()
                .decode("utf-8", errors="ignore")
                .strip()
            )
            if line.startswith("$GNGGA") or line.startswith("$GNRMC"):
                return NMEAParser.parse(line)
            return None
        except Exception as e:
            print(f"Error reading GPS data: {e}")
            return None

    def close(self) -> None:
        self.serial_connection.close()

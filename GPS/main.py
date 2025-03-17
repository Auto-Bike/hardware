import json
import time
from abc import ABC, abstractmethod
from typing import Optional

import redis
import serial

# Redis Configuration
REDIS_HOST = "3.15.51.67"
REDIS_PORT = 6379
BIKE_ID = "bike1"


# --- Interface for Data Store (Interface Segregation & Dependency Inversion) ---
class IDataStore(ABC):
    @abstractmethod
    def push_gps_data(self, bike_id: str, data: dict) -> None:
        pass


# --- Concrete Implementation for Redis ---
class RedisDataStore(IDataStore):
    """Handles Redis interactions."""

    def __init__(self, host: str, port: int):
        self.client = redis.Redis(host=host, port=port, decode_responses=True)

    def push_gps_data(self, bike_id: str, data: dict) -> None:
        try:
            self.client.set(f"gps:{bike_id}", json.dumps(data))
            print("Pushed GPS Data to Redis:", data)
        except Exception as e:
            print("Error pushing GPS data to Redis:", e)


# --- Interface for GPS Reader (Dependency Inversion) ---
class IGPSReader(ABC):
    @abstractmethod
    def read_data(self) -> Optional[dict]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


# --- NMEA Parser (Single Responsibility) ---
class NMEAParser:
    """Parses NMEA GPS sentences."""

    @staticmethod
    def parse(sentence: str) -> Optional[dict]:
        parts = sentence.split(",")
        if parts[0] == "$GNGGA":
            return {
                "type": "GNGGA",
                "latitude": NMEAParser.convert_latitude(parts[2], parts[3]),
                "longitude": NMEAParser.convert_longitude(parts[4], parts[5]),
                "fix_quality": parts[6],
                "satellites": parts[7],
                "altitude": f"{parts[9]} {parts[10]}" if parts[9] else "N/A",
            }
        elif parts[0] == "$GNRMC":
            return {
                "type": "GNRMC",
                "latitude": NMEAParser.convert_latitude(parts[3], parts[4]),
                "longitude": NMEAParser.convert_longitude(parts[5], parts[6]),
                "speed_knots": parts[7],
                "date": parts[9],
                "status": "Valid" if parts[2] == "A" else "Warning",
            }
        return None

    @staticmethod
    def convert_latitude(value: str, direction: str) -> Optional[float]:
        if not value:
            return None
        degrees = float(value[:2])
        minutes = float(value[2:]) / 60
        lat = degrees + minutes
        return round(lat, 6) * (-1 if direction == "S" else 1)

    @staticmethod
    def convert_longitude(value: str, direction: str) -> Optional[float]:
        if not value:
            return None
        degrees = float(value[:3])
        minutes = float(value[3:]) / 60
        lon = degrees + minutes
        return round(lon, 6) * (-1 if direction == "W" else 1)


# --- Concrete Implementation for Serial GPS Reader ---
class SerialGPSReader(IGPSReader):
    """Handles GPS communication and data reading via a serial connection."""

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


# --- GPS Service (Coordinating GPS reading and data storage) ---
class GPSSender:
    """Handles reading GPS data and pushing it to the data store."""

    def __init__(self, bike_id: str, gps_reader: IGPSReader, data_store: IDataStore):
        self.bike_id = bike_id
        self.gps_reader = gps_reader
        self.data_store = data_store

    def send_gps_data(self) -> None:
        try:
            while True:
                data = self.gps_reader.read_data()
                if data:
                    payload = {
                        "bike_id": self.bike_id,
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timestamp": time.time(),
                    }
                    self.data_store.push_gps_data(self.bike_id, payload)
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping GPS reading.")
            self.gps_reader.close()


if __name__ == "__main__":
    data_store = RedisDataStore(REDIS_HOST, REDIS_PORT)
    gps_reader = SerialGPSReader()
    gps_sender = GPSSender(BIKE_ID, gps_reader, data_store)
    gps_sender.send_gps_data()

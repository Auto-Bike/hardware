import json
import redis
import logging


class RedisManager:
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.client = redis.Redis(host=host, port=port, decode_responses=True)

    def push_gps_data(self, bike_id: str, data: dict) -> None:
        try:
            self.client.set(f"gps:{bike_id}", json.dumps(data), ex=30)
            # print("Pushed GPS Data to Redis:", data)
        except Exception as e:
            print("Error pushing GPS data to Redis:", e)

    def acknowledge_connection(self, bike_id: str) -> None:
        try:
            redis_key = f"ack:{bike_id}"
            self.client.set(redis_key, "acknowledged", ex=30)
            logging.info(f"✅ Successfully acknowledged connection for Bike {bike_id}")
        except Exception as e:
            logging.error(f"❌ Failed to send acknowledgment: {str(e)}")

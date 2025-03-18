import signal
import sys
from server.bike import BikeClient

# Global variable to hold our BikeClient instance
bike = None


def cleanup_and_exit(signum, frame):
    global bike
    print("\nReceived termination signal (signal {}). Cleaning up...".format(signum))
    if bike is not None:
        bike.big_motor.cleanup()
        bike.small_motor.cleanup()
    print("GPIO cleaned up successfully.")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers for SIGTERM and SIGINT (Ctrl+C)
    signal.signal(signal.SIGTERM, cleanup_and_exit)
    signal.signal(signal.SIGINT, cleanup_and_exit)

    try:
        bike = BikeClient()
        bike.start()
    except Exception as e:
        print("An error occurred:", e)
    finally:
        if bike is not None:
            bike.big_motor.cleanup()
            bike.small_motor.cleanup()
        print("GPIO cleaned up successfully.")

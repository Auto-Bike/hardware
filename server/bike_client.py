from server.bike import BikeClient

if __name__ == "__main__":
    try:
        bike = BikeClient()
        bike.start()
    except KeyboardInterrupt:
        print("\nExiting program.")
    finally:
        bike.big_motor.cleanup()
        bike.small_motor.cleanup()  # Cleanup all motors
        print("GPIO cleaned up successfully.")

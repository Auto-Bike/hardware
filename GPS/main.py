import serial

class NMEAParser:
    """ Parses NMEA GPS sentences. """

    @staticmethod
    def parse(sentence):
        """ Parses NMEA GNGGA and GNRMC sentences to extract useful GPS data. """
        parts = sentence.split(",")

        if parts[0] == "$GNGGA":
            return {
                "type": "GNGGA",
                "latitude": NMEAParser.convert_latitude(parts[2], parts[3]),
                "longitude": NMEAParser.convert_longitude(parts[4], parts[5]),
                "fix_quality": parts[6],  # 0 = No Fix, 1 = GPS Fix, 2 = DGPS Fix
                "satellites": parts[7],
                "altitude": f"{parts[9]} {parts[10]}" if parts[9] else "N/A"
            }

        elif parts[0] == "$GNRMC":
            return {
                "type": "GNRMC",
                "latitude": NMEAParser.convert_latitude(parts[3], parts[4]),
                "longitude": NMEAParser.convert_longitude(parts[5], parts[6]),
                "speed_knots": parts[7],
                "date": parts[9],
                "status": "Valid" if parts[2] == "A" else "Warning"
            }

        return None  # Ignore other sentence types

    @staticmethod
    def convert_latitude(value, direction):
        """ Converts raw latitude to decimal degrees format. """
        if not value:
            return None
        degrees = float(value[:2])
        minutes = float(value[2:]) / 60
        lat = degrees + minutes
        return round(lat, 6) * (-1 if direction == "S" else 1)

    @staticmethod
    def convert_longitude(value, direction):
        """ Converts raw longitude to decimal degrees format. """
        if not value:
            return None
        degrees = float(value[:3])
        minutes = float(value[3:]) / 60
        lon = degrees + minutes
        return round(lon, 6) * (-1 if direction == "W" else 1)


class GPSModule:
    """ Handles GPS communication and data reading. """

    def __init__(self, port="/dev/ttyAMA0", baudrate=9600):
        self.serial_connection = serial.Serial(port, baudrate, timeout=1)

    def read_data(self):
        """ Reads a raw NMEA sentence from the GPS module. """
        try:
            line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("$GNGGA") or line.startswith("$GNRMC"):
                return NMEAParser.parse(line)
            return None
        except Exception as e:
            print(f"Error reading GPS data: {e}")
            return None

    def close(self):
        """ Closes the serial connection. """
        self.serial_connection.close()


def main():
    gps = GPSModule()

    try:
        while True:
            data = gps.read_data()
            if data:
                print(data)

    except KeyboardInterrupt:
        print("\nStopping GPS reading.")
        gps.close()


if __name__ == "__main__":
    main()

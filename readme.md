# Autonomous Bike Hardware System

This repository contains the hardware control components for the Autonomous Bike project developed for the McMaster University 4OI6 Capstone Course. The system enables an electric bicycle to autonomously navigate to user-defined destinations, addressing the last-mile transportation challenge. The full report is available [here](https://drive.google.com/file/d/1rYNFWow4iSMQe98GnzFRXwHmZjyouQjB/view?usp=drive_link).

## 🛠️ Hardware Overview

The system comprises the following key components:

- **Raspberry Pi 4B**: Serves as the central controller for communication and coordination.
- **ESP32 Microcontroller**: Manages steering via PID control using feedback from a potentiometer.
- **Brushed DC Motor**: Propels the bike movement using PWM signals.
- **BN-220 GPS Module**: Provides real-time latitude and longitude data via UART.
- **Xbox Controller**: Allows for manual override through Bluetooth connectivity.
- **Ultrasonic Sensors** (Optional): Potential future enhancement for obstacle detection.

## 📂 Repository Structure

```
Hardware/
├── Auto_Drive/
│   └── trajectory_replay.py      # Path following commands
├── BLT/
│   ├── motor_control.py          # Motor control via Bluetooth
│   ├── joystick_control.py       # Joystick control script
│   └── joystick_control_log.py   # Joystick control with logging
├── GPS/
│   └── GPS.py                    # Parses UART data from GPS module
├── HC_SR04/                      # Ultrasonic sensor scripts (optional)
├── Motor/
│   └── smallmotor.py             # Steering motor control
├── Redis/                        # Redis-related scripts, Pub/Sub to acknowledge requests
├── Route/                        # Route management scripts, get bike route information though GoogleMaps API
├── server/
│   └── bike_client.py            # Main program for autonomous control
├── socket/                       # Socket communication scripts
├── tof/                          # Time-of-flight sensor scripts (optional)
└── ...
```

## 💻 Running Environment

- **Raspberry Pi 4B**

  - OS: Ubuntu 24.04.2 LTS

  - Python ≥ 3.10

  - Dependencies:

    ```
    pip install pyserial evdev RPi.GPIO
    ```

- **ESP32**

  - Firmware written in C++ to continuously read ADC values and send them to the microcontroller.
  - UART baud rate: 9600 bps
  - Communicates through a serial link.

## ⚙️ How to Run

### 1. Set Up Hardware Connections

- Connect the motor to the ESC and power supply.
- Connect the ESP32 to the Raspberry Pi via USB or GPIO UART.
- Wire the GPS module to the Raspberry Pi's UART (e.g., `/dev/ttyS0`).
- Connect the steering angle feedback potentiometer to the ESP32's ADC.

### 2. Flash the ESP32

Use the Arduino IDE or ESP-IDF to flash the firmware located in the `steering/esp32_firmware` directory.

### 3. Run the Main Control Loop

```
sudo python3 -m server.bike_client
```

This script:

- Reads GPS coordinates.
- Processes route data from the backend.
- Calculates turning angles.
- Sends angle commands to the ESP32.
- Controls the drive motor for movement.

### 4. Manual Override (Optional)

Pair the Xbox controller via Bluetooth and run:

```
sudo python3 -m BLT.joystick_control
```

### 5. Additional Commands

- Run the steering motor:

  ```
  sudo python3 -m Motor.smallmotor
  ```

- Run the GPS module:

  ```
  sudo python3 -m GPS.GPS
  ```

- Path following command:

  ```
  sudo python3 -m Auto_Drive.trajectory_replay
  ```

- Manage the bike service:

  ```
  systemctl daemon-reload
  sudo systemctl restart bike_service
  sudo systemctl status bike_service
  sudo systemctl disable bike_service
  sudo systemctl enable bike_service
  sudo tail -f /var/log/bike_service.log	#view the log file
  ```

## 📡 Communication

- **GPS**: UART → Raspberry Pi
- **ESP32 Steering**: UART → Raspberry Pi
- **Motor Direction**: GPIO → Relay
- **PWM**: Raspberry Pi GPIO → ESC

## 🏆 Capstone Achievement

This project was awarded **3rd Prize** in the 2025 McMaster ECE Capstone Showcase.
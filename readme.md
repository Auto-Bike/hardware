# Autonomous Bike Hardware System

This repository contains all hardware-related software control components of the Autonomous Bike project developed for the McMaster University 4OI6 Capstone Course. The system enables an electric bicycle to autonomously navigate to user-defined destinations, solving the last-mile transportation problem.

## 🛠️ Hardware Overview

The system consists of the following key components:

- **Raspberry Pi 4B**: Acts as the central controller for communication and coordination.
- **ESP32 Microcontroller**: Handles steering via PID control using feedback from an analog angle sensor.
- **Brushless DC Motor with ESC**: Drives the bike forward and backward using PWM signals.
- **BN-220 GPS Module**: Provides real-time latitude and longitude data via UART.
- **Xbox Controller**: Allows for manual override using Bluetooth.
- **Ultrasonic Sensors** (Optional): For future enhancement with obstacle detection.

## 🔧 Hardware Features

- GPIO-controlled direction switching (via relay and level shifters).
- UART-based GPS data parsing and real-time tracking.
- PWM-controlled brushless motor with MOSFET switching.
- Modular Python libraries for steering and driving control.
- PID-based steering control with angle feedback from a potentiometer.

## 📂 Repository Structure

```
hardware/
├── steering/
│   ├── esp32_firmware/        # PID loop and UART handler on ESP32
│   └── pid_controller.py      # Python-side steering controller
├── drive/
│   └── drive_motor.py         # PWM and direction control
├── gps/
│   └── gps_reader.py          # Parses UART data from GPS module
├── controller/
│   └── xbox_controller.py     # Bluetooth Xbox controller handler
└── main_autonomous.py         # Main program for autonomous control
```

## 💻 Running Environment

- **Raspberry Pi 4B**

  - OS: Ubuntu Server 20.04 or Raspberry Pi OS

  - Python ≥ 3.9

  - Dependencies:

    ```
    bash
    pip install pyserial evdev RPi.GPIO
    ```

- **ESP32**

  - Firmware written in Arduino (C++) or ESP-IDF
  - UART baud rate: 9600 bps
  - Communicates with Pi via USB or GPIO UART pins

## ⚙️ How to Run

### 1. Set up Hardware Connections

- Connect the motor to the ESC and power.
- Connect ESP32 to Pi via USB or GPIO UART.
- Wire the GPS module to Pi's UART (e.g., `/dev/ttyS0`).
- Connect steering angle feedback potentiometer to ESP32 ADC.

### 2. Flash the ESP32

Use Arduino IDE or ESP-IDF to flash the firmware in `steering/esp32_firmware`.

### 3. Run the Main Control Loop

```
bash
python3 main_autonomous.py
```

This script:

- Reads GPS coordinates.
- Processes route data from backend.
- Calculates turning angles.
- Sends angle commands to ESP32.
- Controls the drive motor for movement.

### 4. Manual Override (Optional)

Pair the Xbox controller via Bluetooth and run:

```
bash
python3 controller/xbox_controller.py
```

## 📡 Communication

- GPS: UART → Pi
- ESP32 Steering: UART → Pi
- Motor Direction: GPIO → Relay
- PWM: RPi GPIO → ESC

## 🏆 Capstone Achievement

This project was awarded **3rd Prize** in the 2025 McMaster ECE Capstone Showcase.

## 📄 License

MIT License — see `LICENSE` for details.
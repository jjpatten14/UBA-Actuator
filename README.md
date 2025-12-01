# Actuator Controller

Windows desktop application for controlling servo actuators via Bluetooth communication.

## Features

- Modern GUI interface with CustomTkinter
- Bluetooth/Serial device connection and management
- Configurable actuator parameters (position, timing, speed)
- Automated cycling with progress tracking
- Real-time serial terminal for device communication
- Over-The-Air (OTA) firmware updates for connected devices
- Persistent settings storage

## Requirements

- Windows OS
- Python 3.6 or higher
- tkinter (usually included with Python)

## Setup

Run the setup script to create a virtual environment and install dependencies:

```batch
setup.bat
```

## Running the Application

```batch
run.bat
```

## Usage

1. **Settings Tab**: Scan for and connect to your Bluetooth device
2. **Control Tab**: Configure actuator parameters and control cycling
3. **Terminal Tab**: View real-time serial communication
4. **Firmware Tab**: Upload firmware updates to connected devices

## Dependencies

- pyserial >= 3.5
- customtkinter >= 5.2.0

See `requirements.txt` for complete dependency list.

## Project Structure

- `actuator_controller.py` - Main GUI application
- `bluetooth_manager.py` - Bluetooth/serial communication handling
- `settings_manager.py` - Settings persistence management
- `setup.bat` - Installation script
- `run.bat` - Application launcher

## Settings

Application settings are stored in: `%APPDATA%/ActuatorController/settings.json`

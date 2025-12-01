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

## Bluetooth Setup

**Important:** You must pair your ESP32 Bluetooth device with Windows before the application can connect to it.

### Pairing Instructions (Windows)

1. **Enable Bluetooth** on your computer (if not already enabled)

2. **Put your ESP32 device in pairing mode:**
   - Power on the ESP32 device
   - The device should automatically be discoverable (check your ESP32 documentation if needed)

3. **Open Windows Bluetooth Settings:**
   - Press `Windows + I` to open Settings
   - Go to **Devices** → **Bluetooth & other devices**
   - Click **"Add Bluetooth or other device"**
   - Select **"Bluetooth"**

4. **Pair the device:**
   - Your ESP32 device should appear in the list as **"ESP32_Actuator_Controller"**
   - Click on it to pair
   - If prompted for a PIN, enter it (common default: `1234` or `0000`)
   - Wait for "Connected" status

5. **Verify pairing:**
   - The device should now appear in your paired devices list
   - Windows will assign it a COM port (e.g., COM5, COM7)
   - You can check the COM port in Device Manager → Ports (COM & LPT)

**Note:** Once paired, the application will remember your device. You can use the **Settings** tab in the app to scan for and connect to your paired ESP32.

**Troubleshooting:**
- If the device doesn't appear, ensure Bluetooth is enabled on both your computer and the ESP32
- Try turning Bluetooth off and on again on your computer
- Make sure the ESP32 is powered on and within range (~10 meters)

**Linux Users:** Use `bluetoothctl` to pair Bluetooth devices. The process is similar - scan, pair, trust, and connect.

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

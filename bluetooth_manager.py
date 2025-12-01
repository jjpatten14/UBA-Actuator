"""
Bluetooth Manager for Actuator Controller
Handles Bluetooth device scanning, pairing, and serial communication
"""

import serial
import serial.tools.list_ports
import threading
import time
from typing import Callable, Optional, List, Tuple


class BluetoothManager:
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self.connected = False
        self.port_name = None

        # Callback for received data
        self.on_data_received: Optional[Callable[[str], None]] = None
        self.on_connection_changed: Optional[Callable[[bool], None]] = None

        # Reader thread
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_reader = threading.Event()

    def scan_for_devices(self) -> List[Tuple[str, str, str]]:
        """
        Scan for available COM ports (Bluetooth serial ports)
        Returns list of (port, description, hwid) tuples
        """
        devices = []
        ports = serial.tools.list_ports.comports()

        for port in ports:
            # Include all COM ports - user can identify which is the ESP32
            devices.append((port.device, port.description, port.hwid))

        return devices

    def scan_for_bluetooth_devices(self) -> List[Tuple[str, str, str]]:
        """
        Scan specifically for Bluetooth serial ports
        Returns list of (port, description, hwid) tuples
        """
        devices = []
        ports = serial.tools.list_ports.comports()

        for port in ports:
            desc_lower = port.description.lower()
            hwid_lower = port.hwid.lower() if port.hwid else ""

            # Look for Bluetooth-related keywords
            if any(kw in desc_lower for kw in ["bluetooth", "bth", "serial over", "standard serial"]):
                devices.append((port.device, port.description, port.hwid))
            elif "bthenum" in hwid_lower:
                devices.append((port.device, port.description, port.hwid))

        return devices

    def connect(self, port: str, baudrate: int = 115200, timeout: float = 2.0) -> bool:
        """
        Connect to a Bluetooth serial port
        """
        if self.connected:
            self.disconnect()

        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout
            )
            self.port_name = port
            self.connected = True

            # Start reader thread
            self._stop_reader.clear()
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()

            # Notify connection change
            if self.on_connection_changed:
                self.on_connection_changed(True)

            # Send ping to verify connection
            time.sleep(0.5)  # Give ESP32 time to initialize
            self.send_command("PING")

            return True

        except serial.SerialException as e:
            print(f"Connection failed: {e}")
            self.connected = False
            self.serial_port = None
            return False

    def disconnect(self):
        """Disconnect from the current port"""
        self._stop_reader.set()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)

        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass

        self.serial_port = None
        self.connected = False
        self.port_name = None

        if self.on_connection_changed:
            self.on_connection_changed(False)

    def send_command(self, command: str) -> bool:
        """Send a command to the ESP32"""
        if not self.connected or not self.serial_port:
            return False

        try:
            cmd = command.strip() + "\n"
            self.serial_port.write(cmd.encode('utf-8'))
            self.serial_port.flush()
            return True
        except serial.SerialException as e:
            print(f"Send failed: {e}")
            self._handle_disconnect()
            return False

    def send_bytes(self, data: bytes) -> bool:
        """Send raw bytes to the ESP32 (for OTA)"""
        if not self.connected or not self.serial_port:
            return False

        try:
            self.serial_port.write(data)
            self.serial_port.flush()
            return True
        except serial.SerialException as e:
            print(f"Send bytes failed: {e}")
            self._handle_disconnect()
            return False

    def get_serial_port(self) -> Optional[serial.Serial]:
        """Get the raw serial port for direct access (used by OTA)"""
        return self.serial_port if self.connected else None

    def _read_loop(self):
        """Background thread to read incoming data"""
        while not self._stop_reader.is_set():
            if not self.serial_port or not self.connected:
                break

            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line and self.on_data_received:
                        self.on_data_received(line)
                else:
                    time.sleep(0.01)  # Small delay to prevent CPU spinning

            except serial.SerialException as e:
                print(f"Read error: {e}")
                self._handle_disconnect()
                break
            except Exception as e:
                print(f"Unexpected read error: {e}")
                time.sleep(0.1)

    def _handle_disconnect(self):
        """Handle unexpected disconnection"""
        self.connected = False
        if self.on_connection_changed:
            self.on_connection_changed(False)

    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self.connected and self.serial_port is not None

    def get_port_name(self) -> Optional[str]:
        """Get the current port name"""
        return self.port_name if self.connected else None


class CommandProtocol:
    """Helper class for building commands"""

    @staticmethod
    def set_type(actuator_type: int) -> str:
        return f"SET_TYPE:{actuator_type}"

    @staticmethod
    def set_extend(degrees: int) -> str:
        return f"SET_EXTEND:{degrees}"

    @staticmethod
    def set_retract(degrees: int) -> str:
        return f"SET_RETRACT:{degrees}"

    @staticmethod
    def set_dwell_extend(ms: int) -> str:
        return f"SET_DWELL_EXT:{ms}"

    @staticmethod
    def set_dwell_retract(ms: int) -> str:
        return f"SET_DWELL_RET:{ms}"

    @staticmethod
    def set_speed(percent: int) -> str:
        return f"SET_SPEED:{percent}"

    @staticmethod
    def set_cycles(count: int) -> str:
        return f"SET_CYCLES:{count}"

    @staticmethod
    def start() -> str:
        return "START"

    @staticmethod
    def stop() -> str:
        return "STOP"

    @staticmethod
    def pause() -> str:
        return "PAUSE"

    @staticmethod
    def resume() -> str:
        return "RESUME"

    @staticmethod
    def go_home() -> str:
        return "GO_HOME"

    @staticmethod
    def go_extend() -> str:
        return "GO_EXTEND"

    @staticmethod
    def go_retract() -> str:
        return "GO_RETRACT"

    @staticmethod
    def get_status() -> str:
        return "STATUS"

    @staticmethod
    def get_settings() -> str:
        return "GET_SETTINGS"

    @staticmethod
    def ping() -> str:
        return "PING"


def parse_response(response: str) -> Tuple[str, dict]:
    """
    Parse a response from the ESP32
    Returns (response_type, data_dict)
    """
    if ":" not in response:
        return (response, {})

    parts = response.split(":", 1)
    response_type = parts[0]

    if len(parts) < 2 or not parts[1]:
        return (response_type, {})

    data = {}
    pairs = parts[1].split(",")

    for pair in pairs:
        if "=" in pair:
            key, value = pair.split("=", 1)
            # Try to convert to int
            try:
                data[key] = int(value)
            except ValueError:
                data[key] = value

    return (response_type, data)

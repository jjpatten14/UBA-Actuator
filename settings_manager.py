"""
Settings Manager for Actuator Controller
Handles persistent storage of application settings
"""

import json
import os
from pathlib import Path


class SettingsManager:
    DEFAULT_SETTINGS = {
        "actuator_type": 6700,
        "extend_offset": 0,
        "retract_offset": 0,
        "dwell_extend_ms": 2200,
        "dwell_retract_ms": 2200,
        "speed_percent": 100,
        "paired_device": None,
        "paired_device_address": None,
        "window_geometry": None,
    }

    def __init__(self, settings_file: str = None):
        if settings_file is None:
            # Store settings in user's app data folder
            app_data = Path(os.getenv("APPDATA", "."))
            settings_dir = app_data / "ActuatorController"
            settings_dir.mkdir(parents=True, exist_ok=True)
            self.settings_file = settings_dir / "settings.json"
        else:
            self.settings_file = Path(settings_file)

        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> dict:
        """Load settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new settings
                    self.settings = {**self.DEFAULT_SETTINGS, **loaded}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}")
            self.settings = self.DEFAULT_SETTINGS.copy()
        return self.settings

    def save(self) -> bool:
        """Save settings to file"""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value) -> bool:
        """Set a setting value and save"""
        self.settings[key] = value
        return self.save()

    def get_all(self) -> dict:
        """Get all settings"""
        return self.settings.copy()

    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        return self.save()

    # Convenience properties
    @property
    def actuator_type(self) -> int:
        return self.settings["actuator_type"]

    @actuator_type.setter
    def actuator_type(self, value: int):
        self.set("actuator_type", value)

    @property
    def extend_offset(self) -> int:
        return self.settings["extend_offset"]

    @extend_offset.setter
    def extend_offset(self, value: int):
        self.set("extend_offset", value)

    @property
    def retract_offset(self) -> int:
        return self.settings["retract_offset"]

    @retract_offset.setter
    def retract_offset(self, value: int):
        self.set("retract_offset", value)

    @property
    def dwell_extend_ms(self) -> int:
        return self.settings["dwell_extend_ms"]

    @dwell_extend_ms.setter
    def dwell_extend_ms(self, value: int):
        self.set("dwell_extend_ms", value)

    @property
    def dwell_retract_ms(self) -> int:
        return self.settings["dwell_retract_ms"]

    @dwell_retract_ms.setter
    def dwell_retract_ms(self, value: int):
        self.set("dwell_retract_ms", value)

    @property
    def speed_percent(self) -> int:
        return self.settings["speed_percent"]

    @speed_percent.setter
    def speed_percent(self, value: int):
        self.set("speed_percent", value)

    @property
    def paired_device(self) -> str:
        return self.settings["paired_device"]

    @paired_device.setter
    def paired_device(self, value: str):
        self.set("paired_device", value)

    @property
    def paired_device_address(self) -> str:
        return self.settings["paired_device_address"]

    @paired_device_address.setter
    def paired_device_address(self, value: str):
        self.set("paired_device_address", value)

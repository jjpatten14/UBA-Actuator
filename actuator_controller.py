"""
Actuator Cycle Controller - Main GUI Application
Controls ESP32-based servo actuator via Bluetooth
Modern UI with CustomTkinter
"""

import customtkinter as ctk
import threading
import time
import os
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk

from settings_manager import SettingsManager
from bluetooth_manager import BluetoothManager, CommandProtocol, parse_response

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ActuatorControllerApp:
    """Main application class"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Actuator Controller")
        self.root.geometry("680x750")
        self.root.minsize(650, 700)
        self.root.state('zoomed')  # Start maximized

        # Initialize managers
        self.settings = SettingsManager()
        self.bt_manager = BluetoothManager()

        # Set up callbacks
        self.bt_manager.on_data_received = self._on_data_received
        self.bt_manager.on_connection_changed = self._on_connection_changed

        # State variables
        self.is_running = False
        self.is_paused = False
        self.current_cycle = 0
        self.target_cycles = 50
        self.infinite_cycles = ctk.BooleanVar(value=False)

        # Serial terminal state
        self.auto_scroll = ctk.BooleanVar(value=True)

        # Settings tab state
        self.devices = []

        # Firmware/OTA state
        self.ota_file_path = None
        self.ota_in_progress = False
        self.ota_abort_flag = threading.Event()
        self.ota_ready_event = threading.Event()
        self.ota_error_message = None

        # Create UI
        self._create_widgets()
        self._load_settings_to_ui()

        # Try to auto-connect to last device
        self._auto_connect()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """Create all UI widgets"""
        # Create tabview
        self.tabview = ctk.CTkTabview(self.root, width=660, height=700)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        # Make tab buttons 2x larger for touch
        self.tabview._segmented_button.configure(height=64, font=("", 26))

        # Add tabs
        self.tab_control = self.tabview.add("Control")
        self.tab_terminal = self.tabview.add("Terminal")
        self.tab_settings = self.tabview.add("Settings")
        self.tab_firmware = self.tabview.add("Firmware")

        # Build tabs
        self._create_control_tab()
        self._create_terminal_tab()
        self._create_settings_tab()
        self._create_firmware_tab()

    def _create_control_tab(self):
        """Create the main control tab - compact layout with sliders"""
        tab = self.tab_control

        # === Row 1: Type + Connection ===
        row1 = ctk.CTkFrame(tab, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(10, 5))

        # Actuator Type
        type_frame = ctk.CTkFrame(row1)
        type_frame.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(type_frame, text="Type:", font=("", 13)).pack(side="left", padx=10)

        self.actuator_type_var = ctk.IntVar(value=6700)
        self.type_6700_btn = ctk.CTkButton(type_frame, text="6700", width=70, height=36,
                                            command=lambda: self._set_actuator_type(6700))
        self.type_6700_btn.pack(side="left", padx=2, pady=8)

        self.type_6600_btn = ctk.CTkButton(type_frame, text="6600", width=70, height=36,
                                            fg_color="gray40", hover_color="gray50",
                                            command=lambda: self._set_actuator_type(6600))
        self.type_6600_btn.pack(side="left", padx=2, pady=8)

        # Connection status
        conn_frame = ctk.CTkFrame(row1)
        conn_frame.pack(side="right")

        self.conn_indicator = ctk.CTkLabel(conn_frame, text="●", font=("", 20),
                                            text_color="#AA0000")
        self.conn_indicator.pack(side="left", padx=10)

        self.conn_label = ctk.CTkLabel(conn_frame, text="Disconnected", font=("", 13))
        self.conn_label.pack(side="left", padx=(0, 10), pady=8)

        # === Row 2: Position + Timing Controls (side by side) ===
        row2 = ctk.CTkFrame(tab)
        row2.pack(fill="x", padx=10, pady=5)

        # Left side - Positions (degrees)
        pos_frame = ctk.CTkFrame(row2)
        pos_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ctk.CTkLabel(pos_frame, text="Position (degrees)", font=("", 13, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        # Extend slider with +/- buttons
        ext_row = ctk.CTkFrame(pos_frame, fg_color="transparent")
        ext_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(ext_row, text="Extend", font=("", 12), width=55).pack(side="left")
        ctk.CTkButton(ext_row, text="-", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_extend(-1)).pack(side="left", padx=2)
        self.extend_slider = ctk.CTkSlider(ext_row, from_=0, to=90, width=200, height=35,
                                            command=self._on_extend_changed)
        self.extend_slider.pack(side="left", padx=5)
        self.extend_slider.set(0)
        ctk.CTkButton(ext_row, text="+", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_extend(1)).pack(side="left", padx=2)
        self.extend_label = ctk.CTkLabel(ext_row, text="0°", font=("", 14, "bold"), width=45)
        self.extend_label.pack(side="left", padx=5)

        # Retract slider with +/- buttons
        ret_row = ctk.CTkFrame(pos_frame, fg_color="transparent")
        ret_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(ret_row, text="Retract", font=("", 12), width=55).pack(side="left")
        ctk.CTkButton(ret_row, text="-", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_retract(-1)).pack(side="left", padx=2)
        self.retract_slider = ctk.CTkSlider(ret_row, from_=0, to=90, width=200, height=35,
                                             command=self._on_retract_changed)
        self.retract_slider.pack(side="left", padx=5)
        self.retract_slider.set(0)
        ctk.CTkButton(ret_row, text="+", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_retract(1)).pack(side="left", padx=2)
        self.retract_label = ctk.CTkLabel(ret_row, text="0°", font=("", 14, "bold"), width=45)
        self.retract_label.pack(side="left", padx=5)

        # Right side - Timing (seconds)
        time_frame = ctk.CTkFrame(row2)
        time_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ctk.CTkLabel(time_frame, text="Dwell Time (seconds)", font=("", 13, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        # Dwell Extend slider with +/- buttons
        dwell_ext_row = ctk.CTkFrame(time_frame, fg_color="transparent")
        dwell_ext_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(dwell_ext_row, text="Extend", font=("", 12), width=55).pack(side="left")
        ctk.CTkButton(dwell_ext_row, text="-", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_dwell_extend(-0.1)).pack(side="left", padx=2)
        self.dwell_extend_slider = ctk.CTkSlider(dwell_ext_row, from_=0.1, to=3.5, width=200, height=35,
                                                  command=self._on_dwell_extend_changed)
        self.dwell_extend_slider.pack(side="left", padx=5)
        self.dwell_extend_slider.set(2.0)
        ctk.CTkButton(dwell_ext_row, text="+", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_dwell_extend(0.1)).pack(side="left", padx=2)
        self.dwell_extend_label = ctk.CTkLabel(dwell_ext_row, text="2.0s", font=("", 14, "bold"), width=45)
        self.dwell_extend_label.pack(side="left", padx=5)

        # Dwell Retract slider with +/- buttons
        dwell_ret_row = ctk.CTkFrame(time_frame, fg_color="transparent")
        dwell_ret_row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(dwell_ret_row, text="Retract", font=("", 12), width=55).pack(side="left")
        ctk.CTkButton(dwell_ret_row, text="-", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_dwell_retract(-0.1)).pack(side="left", padx=2)
        self.dwell_retract_slider = ctk.CTkSlider(dwell_ret_row, from_=0.1, to=3.5, width=200, height=35,
                                                   command=self._on_dwell_retract_changed)
        self.dwell_retract_slider.pack(side="left", padx=5)
        self.dwell_retract_slider.set(2.0)
        ctk.CTkButton(dwell_ret_row, text="+", width=50, height=45, font=("", 18),
                      command=lambda: self._adjust_dwell_retract(0.1)).pack(side="left", padx=2)
        self.dwell_retract_label = ctk.CTkLabel(dwell_ret_row, text="2.0s", font=("", 14, "bold"), width=45)
        self.dwell_retract_label.pack(side="left", padx=5)

        # === Row 3: Speed + Cycles ===
        row3 = ctk.CTkFrame(tab, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=5)

        # Speed slider
        speed_frame = ctk.CTkFrame(row3)
        speed_frame.pack(side="left", expand=True, fill="x", padx=(0, 5))

        ctk.CTkLabel(speed_frame, text="Speed", font=("", 13)).pack(side="left", padx=10)
        self.speed_var = ctk.IntVar(value=100)
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=1, to=100,
                                           variable=self.speed_var, width=150,
                                           command=self._on_speed_changed)
        self.speed_slider.pack(side="left", padx=5, pady=12)
        self.speed_label = ctk.CTkLabel(speed_frame, text="100%", font=("", 13), width=45)
        self.speed_label.pack(side="left", padx=5)

        # Cycles
        cycle_frame = ctk.CTkFrame(row3)
        cycle_frame.pack(side="right", padx=(5, 0))

        ctk.CTkLabel(cycle_frame, text="Cycles:", font=("", 13)).pack(side="left", padx=(10, 5))

        ctk.CTkButton(cycle_frame, text="-", width=35, height=32,
                      command=lambda: self._adjust_cycles(-10)).pack(side="left", padx=2)

        self.cycles_var = ctk.IntVar(value=50)
        self.cycles_label = ctk.CTkLabel(cycle_frame, textvariable=self.cycles_var,
                                          font=("", 16, "bold"), width=60)
        self.cycles_label.pack(side="left", padx=5)

        ctk.CTkButton(cycle_frame, text="+", width=35, height=32,
                      command=lambda: self._adjust_cycles(10)).pack(side="left", padx=2)

        ctk.CTkCheckBox(cycle_frame, text="∞", variable=self.infinite_cycles,
                        width=40, command=self._on_infinite_changed).pack(side="left", padx=(10, 10), pady=8)

        # === Row 4: Progress ===
        row4 = ctk.CTkFrame(tab, fg_color="transparent")
        row4.pack(fill="x", padx=10, pady=5)

        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(row4, variable=self.progress_var,
                                                width=400, height=20)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(row4, text="0 / 50 cycles", font=("", 12))
        self.progress_label.pack(pady=(5, 0))

        # === Row 5: Main Control Buttons ===
        row5 = ctk.CTkFrame(tab, fg_color="transparent")
        row5.pack(fill="x", padx=10, pady=10)

        btn_frame = ctk.CTkFrame(row5, fg_color="transparent")
        btn_frame.pack(expand=True)

        self.start_btn = ctk.CTkButton(btn_frame, text="▶ START", width=130, height=50,
                                        font=("", 16, "bold"), fg_color="#1f9e4a",
                                        hover_color="#178a3e", command=self._start_cycles)
        self.start_btn.pack(side="left", padx=5)

        self.pause_btn = ctk.CTkButton(btn_frame, text="⏸ PAUSE", width=130, height=50,
                                        font=("", 16, "bold"), fg_color="#d97706",
                                        hover_color="#b45309", command=self._pause_cycles,
                                        state="disabled")
        self.pause_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ STOP", width=130, height=50,
                                       font=("", 16, "bold"), fg_color="#dc2626",
                                       hover_color="#b91c1c", command=self._stop_cycles,
                                       state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # === Row 6: Override Buttons ===
        row6 = ctk.CTkFrame(tab, fg_color="transparent")
        row6.pack(fill="x", padx=10, pady=(0, 10))

        override_frame = ctk.CTkFrame(row6, fg_color="transparent")
        override_frame.pack(expand=True)

        self.home_btn = ctk.CTkButton(override_frame, text="HOME", width=100, height=36,
                                       fg_color="gray40", hover_color="gray50",
                                       command=self._go_home)
        self.home_btn.pack(side="left", padx=5)

        self.extend_btn = ctk.CTkButton(override_frame, text="EXTEND", width=100, height=36,
                                         fg_color="gray40", hover_color="gray50",
                                         command=self._go_extend)
        self.extend_btn.pack(side="left", padx=5)

        self.retract_btn = ctk.CTkButton(override_frame, text="RETRACT", width=100, height=36,
                                          fg_color="gray40", hover_color="gray50",
                                          command=self._go_retract)
        self.retract_btn.pack(side="left", padx=5)

        # === Status Bar ===
        status_frame = ctk.CTkFrame(tab)
        status_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(status_frame, text="Status:", font=("", 11)).pack(side="left", padx=(10, 5), pady=5)
        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var,
                                          font=("", 11, "italic"))
        self.status_label.pack(side="left", pady=5)

    def _on_extend_changed(self, value):
        """Handle extend slider change"""
        val = int(value)
        self.extend_label.configure(text=f"{val}°")
        self.settings.extend_offset = val
        self.bt_manager.send_command(CommandProtocol.set_extend(val))

    def _on_retract_changed(self, value):
        """Handle retract slider change"""
        val = int(value)
        self.retract_label.configure(text=f"{val}°")
        self.settings.retract_offset = val
        self.bt_manager.send_command(CommandProtocol.set_retract(val))

    def _on_dwell_extend_changed(self, value):
        """Handle dwell extend slider change"""
        self.dwell_extend_label.configure(text=f"{value:.1f}s")
        ms = int(value * 1000)
        self.settings.dwell_extend_ms = ms
        self.bt_manager.send_command(CommandProtocol.set_dwell_extend(ms))

    def _on_dwell_retract_changed(self, value):
        """Handle dwell retract slider change"""
        self.dwell_retract_label.configure(text=f"{value:.1f}s")
        ms = int(value * 1000)
        self.settings.dwell_retract_ms = ms
        self.bt_manager.send_command(CommandProtocol.set_dwell_retract(ms))

    def _adjust_extend(self, delta):
        """Adjust extend position by delta (±1 degree)"""
        current = self.extend_slider.get()
        new_val = max(0, min(90, int(current) + delta))
        self.extend_slider.set(new_val)
        self._on_extend_changed(new_val)

    def _adjust_retract(self, delta):
        """Adjust retract position by delta (±1 degree)"""
        current = self.retract_slider.get()
        new_val = max(0, min(90, int(current) + delta))
        self.retract_slider.set(new_val)
        self._on_retract_changed(new_val)

    def _adjust_dwell_extend(self, delta):
        """Adjust dwell extend time by delta (±0.1 seconds)"""
        current = self.dwell_extend_slider.get()
        new_val = max(0.1, min(3.5, round(current + delta, 1)))
        self.dwell_extend_slider.set(new_val)
        self._on_dwell_extend_changed(new_val)

    def _adjust_dwell_retract(self, delta):
        """Adjust dwell retract time by delta (±0.1 seconds)"""
        current = self.dwell_retract_slider.get()
        new_val = max(0.1, min(3.5, round(current + delta, 1)))
        self.dwell_retract_slider.set(new_val)
        self._on_dwell_retract_changed(new_val)

    def _create_terminal_tab(self):
        """Create the serial terminal tab"""
        tab = self.tab_terminal

        # Output area
        output_frame = ctk.CTkFrame(tab)
        output_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.serial_output = ctk.CTkTextbox(output_frame, font=("Consolas", 11),
                                             state="disabled", wrap="word")
        self.serial_output.pack(fill="both", expand=True)

        # Configure tags for coloring
        self.serial_output._textbox.tag_configure("timestamp", foreground="gray")
        self.serial_output._textbox.tag_configure("sent", foreground="#3b8ed0")
        self.serial_output._textbox.tag_configure("received", foreground="#1f9e4a")
        self.serial_output._textbox.tag_configure("error", foreground="#dc2626")

        # Input area
        input_frame = ctk.CTkFrame(tab, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.serial_input = ctk.CTkEntry(input_frame, font=("Consolas", 12),
                                          placeholder_text="Enter command...")
        self.serial_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.serial_input.bind("<Return>", lambda e: self._send_serial_command())

        ctk.CTkButton(input_frame, text="Send", width=80,
                      command=self._send_serial_command).pack(side="right")

        # Controls
        ctrl_frame = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkCheckBox(ctrl_frame, text="Auto-scroll",
                        variable=self.auto_scroll).pack(side="left")

        ctk.CTkButton(ctrl_frame, text="Clear", width=70,
                      command=self._clear_serial_output).pack(side="right")

        # Quick commands
        quick_frame = ctk.CTkFrame(tab, fg_color="transparent")
        quick_frame.pack(fill="x", padx=10, pady=5)

        for label, cmd in [("PING", "PING"), ("STATUS", "STATUS"), ("SETTINGS", "GET_SETTINGS")]:
            ctk.CTkButton(quick_frame, text=label, width=90, height=32,
                          fg_color="gray40", hover_color="gray50",
                          command=lambda c=cmd: self._send_quick_command(c)).pack(side="left", padx=5)

    def _create_settings_tab(self):
        """Create the settings tab - Touch-friendly version with 3x scaling"""
        tab = self.tab_settings

        # Create scrollable frame for touch-friendly content
        scroll_frame = ctk.CTkScrollableFrame(tab, width=640, height=700)
        scroll_frame.pack(fill="both", expand=True)

        # Bluetooth Connection
        bt_frame = ctk.CTkFrame(scroll_frame)
        bt_frame.pack(fill="x", padx=30, pady=30)

        ctk.CTkLabel(bt_frame, text="Bluetooth Connection",
                     font=("", 42, "bold")).pack(anchor="w", padx=30, pady=(30, 15))

        # Device list - Touch-friendly with larger font
        self.device_listbox = tk.Listbox(bt_frame, height=4, font=("Segoe UI", 33),
                                          bg="#2b2b2b", fg="white", selectbackground="#3b8ed0",
                                          highlightthickness=0, bd=0)
        self.device_listbox.pack(fill="x", padx=30, pady=15)

        # Buttons - Horizontal layout, 33% smaller
        btn_frame = ctk.CTkFrame(bt_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkButton(btn_frame, text="Scan", width=268, height=64,
                      font=("", 24), command=self._scan_devices).pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="Connect", width=268, height=64,
                      font=("", 24), command=self._connect_device).pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="Disconnect", width=268, height=64,
                      font=("", 24), command=self._disconnect_device).pack(side="left", padx=15)

        self.settings_status_var = ctk.StringVar(value="Not connected")
        ctk.CTkLabel(bt_frame, textvariable=self.settings_status_var,
                     font=("", 33, "italic")).pack(anchor="w", padx=30, pady=(15, 30))

        # Paired device
        paired_frame = ctk.CTkFrame(scroll_frame)
        paired_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkLabel(paired_frame, text="Paired Device",
                     font=("", 28, "bold")).pack(anchor="w", padx=30, pady=(30, 15))

        paired_name = self.settings.paired_device or "None"
        self.paired_label = ctk.CTkLabel(paired_frame, text=f"Device: {paired_name}",
                                          font=("", 22))
        self.paired_label.pack(anchor="w", padx=30, pady=15)

        ctk.CTkButton(paired_frame, text="Forget Device", width=241, height=64,
                      font=("", 24), command=self._forget_device).pack(anchor="w", padx=30, pady=(0, 30))

        # Reset
        reset_frame = ctk.CTkFrame(scroll_frame)
        reset_frame.pack(fill="x", padx=30, pady=15)

        ctk.CTkButton(reset_frame, text="Reset All Settings", width=450, height=96,
                      font=("", 24), fg_color="#dc2626", hover_color="#b91c1c",
                      command=self._reset_settings).pack(padx=30, pady=45)

        # Scan on creation
        self._scan_devices()

    def _create_firmware_tab(self):
        """Create the firmware tab"""
        tab = self.tab_firmware

        # Info
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(info_frame, text="Firmware Update (OTA)", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(info_frame, text="Update ESP32 firmware wirelessly via Bluetooth.",
                     font=("", 11)).pack(anchor="w", padx=10, pady=(0, 10))

        # File selection
        file_frame = ctk.CTkFrame(tab)
        file_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(file_frame, text="Firmware File", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        self.firmware_path_var = ctk.StringVar(value="No file selected")
        ctk.CTkLabel(file_frame, textvariable=self.firmware_path_var,
                     font=("", 11), wraplength=400).pack(anchor="w", padx=10, pady=5)

        ctk.CTkButton(file_frame, text="Browse...", width=120,
                      command=self._browse_firmware).pack(anchor="w", padx=10, pady=(0, 5))

        self.firmware_info_var = ctk.StringVar(value="")
        ctk.CTkLabel(file_frame, textvariable=self.firmware_info_var,
                     font=("", 10, "italic")).pack(anchor="w", padx=10, pady=(0, 10))

        # Progress
        progress_frame = ctk.CTkFrame(tab)
        progress_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(progress_frame, text="Upload Progress", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        self.ota_progress_var = ctk.DoubleVar(value=0)
        self.ota_progress_bar = ctk.CTkProgressBar(progress_frame, variable=self.ota_progress_var,
                                                    width=400, height=15)
        self.ota_progress_bar.pack(fill="x", padx=10, pady=5)
        self.ota_progress_bar.set(0)

        self.ota_status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(progress_frame, textvariable=self.ota_status_var,
                     font=("", 11)).pack(anchor="w", padx=10, pady=(0, 10))

        # Upload controls
        upload_frame = ctk.CTkFrame(tab, fg_color="transparent")
        upload_frame.pack(fill="x", padx=10, pady=5)

        self.upload_btn = ctk.CTkButton(upload_frame, text="Upload Firmware", width=150,
                                         fg_color="#1f9e4a", hover_color="#178a3e",
                                         command=self._start_ota_upload)
        self.upload_btn.pack(side="left", padx=5)

        self.abort_btn = ctk.CTkButton(upload_frame, text="Abort", width=100,
                                        fg_color="#dc2626", hover_color="#b91c1c",
                                        command=self._abort_ota_upload, state="disabled")
        self.abort_btn.pack(side="left", padx=5)

        # Version
        version_frame = ctk.CTkFrame(tab)
        version_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(version_frame, text="Device Info", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        ver_row = ctk.CTkFrame(version_frame, fg_color="transparent")
        ver_row.pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(ver_row, text="Version:", font=("", 11)).pack(side="left")
        self.device_version_var = ctk.StringVar(value="Unknown")
        ctk.CTkLabel(ver_row, textvariable=self.device_version_var,
                     font=("", 11, "bold")).pack(side="left", padx=10)

        ctk.CTkButton(version_frame, text="Check Version", width=120,
                      command=self._check_firmware_version).pack(anchor="w", padx=10, pady=(0, 10))

    # === Settings Tab Methods ===
    def _scan_devices(self):
        self.device_listbox.delete(0, tk.END)
        self.devices = self.bt_manager.scan_for_devices()
        if not self.devices:
            self.device_listbox.insert(tk.END, "No devices found")
        else:
            for port, desc, hwid in self.devices:
                self.device_listbox.insert(tk.END, f"{port} - {desc}")

    def _connect_device(self):
        selection = self.device_listbox.curselection()
        if not selection or not self.devices:
            messagebox.showwarning("No Selection", "Please select a device")
            return

        idx = selection[0]
        if idx >= len(self.devices):
            return

        port, desc, hwid = self.devices[idx]
        self.settings_status_var.set(f"Connecting to {port}...")
        self.root.update()

        if self.bt_manager.connect(port):
            self.settings.paired_device = desc
            self.settings.paired_device_address = port
            self.paired_label.configure(text=f"Device: {desc}")
            self._update_settings_status()
            self._sync_settings_to_esp32()
        else:
            messagebox.showerror("Connection Failed", f"Could not connect to {port}")
            self._update_settings_status()

    def _disconnect_device(self):
        self.bt_manager.disconnect()
        self._update_settings_status()

    def _forget_device(self):
        self.settings.paired_device = None
        self.settings.paired_device_address = None
        self.paired_label.configure(text="Device: None")

    def _reset_settings(self):
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.settings.reset_to_defaults()
            messagebox.showinfo("Reset Complete", "Settings reset. Please restart.")

    def _update_settings_status(self):
        if self.bt_manager.is_connected():
            port = self.bt_manager.get_port_name()
            self.settings_status_var.set(f"Connected ({port})")
        else:
            self.settings_status_var.set("Not connected")

    # === Firmware Tab Methods ===
    def _browse_firmware(self):
        file_path = filedialog.askopenfilename(
            title="Select Firmware File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if file_path:
            self.ota_file_path = file_path
            self.firmware_path_var.set(os.path.basename(file_path))
            file_size = os.path.getsize(file_path)
            self.firmware_info_var.set(f"Size: {file_size / 1024:.1f} KB")
        else:
            self.ota_file_path = None
            self.firmware_path_var.set("No file selected")
            self.firmware_info_var.set("")

    def _check_firmware_version(self):
        if not self.bt_manager.is_connected():
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        self.bt_manager.send_command("GET_VERSION")
        self._append_serial_output(">>> GET_VERSION", "sent")

    def _start_ota_upload(self):
        if not self.bt_manager.is_connected():
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        if not self.ota_file_path or not os.path.exists(self.ota_file_path):
            messagebox.showwarning("No File", "Please select a firmware file")
            return
        if self.ota_in_progress:
            return

        file_size = os.path.getsize(self.ota_file_path)
        if not messagebox.askyesno("Confirm Upload",
                                    f"Upload firmware?\n\nFile: {os.path.basename(self.ota_file_path)}\n"
                                    f"Size: {file_size:,} bytes"):
            return

        self.ota_in_progress = True
        self.ota_abort_flag.clear()
        self.upload_btn.configure(state="disabled")
        self.abort_btn.configure(state="normal")
        self.ota_progress_var.set(0)
        self.ota_status_var.set("Starting upload...")

        threading.Thread(target=self._ota_upload_thread, daemon=True).start()

    def _abort_ota_upload(self):
        if self.ota_in_progress:
            self.ota_abort_flag.set()
            self.bt_manager.send_command("OTA_ABORT")
            self._append_serial_output(">>> OTA_ABORT", "sent")

    def _ota_upload_thread(self):
        try:
            file_size = os.path.getsize(self.ota_file_path)
            chunk_size = 512
            ready_timeout = 5.0

            self.ota_ready_event.clear()
            self.ota_error_message = None

            self.bt_manager.send_command(f"OTA_START:{file_size}")
            self.root.after(0, lambda: self._append_serial_output(f">>> OTA_START:{file_size}", "sent"))
            self.root.after(0, lambda: self.ota_status_var.set("Waiting for device ready..."))

            if not self.ota_ready_event.wait(timeout=ready_timeout):
                if self.ota_error_message:
                    self._ota_finish(f"Device error: {self.ota_error_message}")
                else:
                    self._ota_finish("Timeout waiting for device ready")
                return

            if self.ota_error_message:
                return

            if self.ota_abort_flag.is_set():
                self._ota_finish("Aborted by user")
                return

            bytes_sent = 0
            last_success_time = time.time()

            with open(self.ota_file_path, 'rb') as f:
                while bytes_sent < file_size:
                    if self.ota_abort_flag.is_set():
                        self._ota_finish("Aborted by user")
                        return

                    if not self.bt_manager.is_connected():
                        self._ota_finish("Connection lost")
                        return

                    if time.time() - last_success_time > 5.0:
                        self._ota_finish("Upload timeout")
                        return

                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    if not self.bt_manager.send_bytes(chunk):
                        self._ota_finish("Failed to send data")
                        return

                    last_success_time = time.time()
                    bytes_sent += len(chunk)
                    progress = bytes_sent / file_size

                    self.root.after(0, lambda p=progress, b=bytes_sent, t=file_size:
                                    self._update_ota_progress(p, b, t))
                    time.sleep(0.02)

            self.root.after(0, lambda: self.ota_status_var.set("Verifying..."))
            time.sleep(2)
            self._ota_finish("Upload complete - device restarting", success=True)

        except Exception as e:
            self._ota_finish(f"Error: {str(e)}")

    def _update_ota_progress(self, progress, bytes_sent, total):
        self.ota_progress_var.set(progress)
        self.ota_progress_bar.set(progress)
        self.ota_status_var.set(f"Uploading: {bytes_sent:,} / {total:,} bytes ({progress * 100:.1f}%)")

    def _ota_finish(self, message, success=False):
        def update_ui():
            self.ota_in_progress = False
            self.upload_btn.configure(state="normal")
            self.abort_btn.configure(state="disabled")
            self.ota_status_var.set(message)

            if success:
                self.ota_progress_var.set(1.0)
                self.ota_progress_bar.set(1.0)
                messagebox.showinfo("OTA Complete", "Firmware uploaded!\nDevice restarting.")
            else:
                self.ota_progress_var.set(0)
                self.ota_progress_bar.set(0)

        self.root.after(0, update_ui)

    # === Serial Terminal Methods ===
    def _send_serial_command(self):
        cmd = self.serial_input.get().strip()
        if not cmd:
            return
        if not self.bt_manager.is_connected():
            self._append_serial_output("Not connected!", "error")
            return
        self._append_serial_output(f">>> {cmd}", "sent")
        self.bt_manager.send_command(cmd)
        self.serial_input.delete(0, tk.END)

    def _send_quick_command(self, cmd):
        if not self.bt_manager.is_connected():
            self._append_serial_output("Not connected!", "error")
            return
        self._append_serial_output(f">>> {cmd}", "sent")
        self.bt_manager.send_command(cmd)

    def _append_serial_output(self, text, tag="received"):
        self.serial_output.configure(state="normal")
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.serial_output._textbox.insert(tk.END, timestamp, "timestamp")
        self.serial_output._textbox.insert(tk.END, text + "\n", tag)
        self.serial_output.configure(state="disabled")
        if self.auto_scroll.get():
            self.serial_output._textbox.see(tk.END)

    def _clear_serial_output(self):
        self.serial_output.configure(state="normal")
        self.serial_output._textbox.delete(1.0, tk.END)
        self.serial_output.configure(state="disabled")

    # === Control Methods ===
    def _set_actuator_type(self, type_val):
        self.actuator_type_var.set(type_val)
        if type_val == 6700:
            self.type_6700_btn.configure(fg_color=["#3b8ed0", "#1f6aa5"])
            self.type_6600_btn.configure(fg_color="gray40")
        else:
            self.type_6600_btn.configure(fg_color=["#3b8ed0", "#1f6aa5"])
            self.type_6700_btn.configure(fg_color="gray40")
        self.settings.actuator_type = type_val
        self.bt_manager.send_command(CommandProtocol.set_type(type_val))

    def _on_speed_changed(self, value):
        val = int(value)
        self.speed_label.configure(text=f"{val}%")
        self.settings.speed_percent = val
        self.bt_manager.send_command(CommandProtocol.set_speed(val))

    def _adjust_cycles(self, delta):
        current = self.cycles_var.get()
        new_val = max(1, min(100000, current + delta))
        self.cycles_var.set(new_val)
        self.target_cycles = new_val
        self.bt_manager.send_command(CommandProtocol.set_cycles(new_val))
        self._update_progress()

    def _on_infinite_changed(self):
        if self.infinite_cycles.get():
            self.progress_bar.configure(mode="indeterminate")
        else:
            self.progress_bar.configure(mode="determinate")
        self._update_progress()

    def _go_home(self):
        if not self.bt_manager.is_connected():
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        self.bt_manager.send_command(CommandProtocol.go_home())
        self.status_var.set("Moving to HOME")

    def _go_extend(self):
        if not self.bt_manager.is_connected():
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        self.bt_manager.send_command(CommandProtocol.go_extend())
        self.status_var.set("Moving to EXTEND")

    def _go_retract(self):
        if not self.bt_manager.is_connected():
            messagebox.showwarning("Not Connected", "Please connect first")
            return
        self.bt_manager.send_command(CommandProtocol.go_retract())
        self.status_var.set("Moving to RETRACT")

    def _start_cycles(self):
        if not self.bt_manager.is_connected():
            messagebox.showwarning("Not Connected", "Please connect first")
            return

        self.current_cycle = 0

        if self.infinite_cycles.get():
            self.bt_manager.send_command(CommandProtocol.set_cycles(0))
        else:
            self.target_cycles = self.cycles_var.get()
            self.bt_manager.send_command(CommandProtocol.set_cycles(self.target_cycles))

        self._update_progress()
        self.bt_manager.send_command(CommandProtocol.start())

        self.is_running = True
        self.is_paused = False
        self._update_button_states()
        self.status_var.set("Running cycles...")

    def _pause_cycles(self):
        if not self.bt_manager.is_connected():
            return

        if self.is_paused:
            self.bt_manager.send_command(CommandProtocol.resume())
            self.is_paused = False
            self.status_var.set("Resumed")
        else:
            self.bt_manager.send_command(CommandProtocol.pause())
            self.is_paused = True
            self.status_var.set("Paused")

        self._update_button_states()

    def _stop_cycles(self):
        if not self.bt_manager.is_connected():
            return

        self.bt_manager.send_command(CommandProtocol.stop())
        self.is_running = False
        self.is_paused = False
        self._update_button_states()
        self.status_var.set("Stopped - at EXTEND")

    def _update_progress(self):
        if self.infinite_cycles.get():
            self.progress_label.configure(text=f"{self.current_cycle} cycles (infinite)")
        else:
            if self.target_cycles > 0:
                percent = self.current_cycle / self.target_cycles
                self.progress_var.set(percent)
                self.progress_bar.set(percent)
            self.progress_label.configure(text=f"{self.current_cycle} / {self.target_cycles} cycles")

    def _update_button_states(self):
        if self.is_running:
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            self.stop_btn.configure(state="normal")
            self.home_btn.configure(state="disabled")
            self.extend_btn.configure(state="disabled")
            self.retract_btn.configure(state="disabled")

            if self.is_paused:
                self.pause_btn.configure(text="▶ RESUME")
            else:
                self.pause_btn.configure(text="⏸ PAUSE")
        else:
            self.start_btn.configure(state="normal")
            self.pause_btn.configure(state="disabled", text="⏸ PAUSE")
            self.stop_btn.configure(state="disabled")
            self.home_btn.configure(state="normal")
            self.extend_btn.configure(state="normal")
            self.retract_btn.configure(state="normal")

    # === Data Handling ===
    def _on_data_received(self, data):
        self.root.after(0, lambda: self._process_response(data))

    def _process_response(self, data):
        self._append_serial_output(data, "received")

        resp_type, resp_data = parse_response(data)

        if resp_type == "PONG":
            self.status_var.set("Connected - Ready")
        elif resp_type == "STATUS":
            state = resp_data.get("STATE", "UNKNOWN")
            pos = resp_data.get("POS", 0)
            self.status_var.set(f"{state} - Position: {pos}°")
        elif resp_type == "PROGRESS":
            cycle = resp_data.get("CYCLE", 0)
            target = resp_data.get("TARGET", 0)
            self.current_cycle = cycle
            if not self.infinite_cycles.get():
                self.target_cycles = target
            self._update_progress()
        elif resp_type == "COMPLETE":
            cycles = resp_data.get("CYCLES", 0)
            self.status_var.set(f"Complete - {cycles} cycles finished")
            self.is_running = False
            self.is_paused = False
            self._update_button_states()
        elif resp_type == "OK":
            if "OTA_READY" in data:
                self.ota_status_var.set("Device ready - sending...")
                self.ota_ready_event.set()
        elif resp_type == "VERSION":
            version = data.split(":", 1)[1] if ":" in data else "Unknown"
            self.device_version_var.set(version)
        elif resp_type == "OTA_PROGRESS":
            parts = data.split(":")
            if len(parts) >= 2:
                try:
                    percent = int(parts[1]) / 100
                    self.ota_progress_var.set(percent)
                    self.ota_progress_bar.set(percent)
                except ValueError:
                    pass
        elif resp_type == "ERR":
            self.status_var.set(f"Error: {data}")
            if "OTA" in data:
                self.ota_error_message = data
                self.ota_ready_event.set()
                if self.ota_in_progress:
                    self._ota_finish(f"OTA Error: {data}")

    def _on_connection_changed(self, connected):
        self.root.after(0, lambda: self._update_connection_ui(connected))

    def _update_connection_ui(self, connected):
        self._update_settings_status()

        if connected:
            port = self.bt_manager.get_port_name()
            self.conn_indicator.configure(text_color="#1f9e4a")
            self.conn_label.configure(text=f"Connected ({port})")
            self.status_var.set("Connected")
            self._append_serial_output(f"Connected to {port}", "received")
        else:
            self.conn_indicator.configure(text_color="#dc2626")
            self.conn_label.configure(text="Disconnected")
            self.status_var.set("Disconnected")
            self._append_serial_output("Disconnected", "error")
            if self.is_running:
                self.is_running = False
                self.is_paused = False
                self._update_button_states()

    def _load_settings_to_ui(self):
        self.actuator_type_var.set(self.settings.actuator_type)
        self._set_actuator_type(self.settings.actuator_type)

        # Set slider values after a delay (widgets must exist)
        def set_values():
            # Position sliders
            self.extend_slider.set(self.settings.extend_offset)
            self.extend_label.configure(text=f"{self.settings.extend_offset}°")
            self.retract_slider.set(self.settings.retract_offset)
            self.retract_label.configure(text=f"{self.settings.retract_offset}°")

            # Timing sliders
            dwell_ext_sec = self.settings.dwell_extend_ms / 1000.0
            dwell_ret_sec = self.settings.dwell_retract_ms / 1000.0
            self.dwell_extend_slider.set(dwell_ext_sec)
            self.dwell_extend_label.configure(text=f"{dwell_ext_sec:.1f}s")
            self.dwell_retract_slider.set(dwell_ret_sec)
            self.dwell_retract_label.configure(text=f"{dwell_ret_sec:.1f}s")

            # Speed
            self.speed_var.set(self.settings.speed_percent)
            self.speed_label.configure(text=f"{self.settings.speed_percent}%")

        self.root.after(200, set_values)

    def _auto_connect(self):
        port = self.settings.paired_device_address
        if port:
            self.status_var.set(f"Connecting to {port}...")
            self.root.update()

            def connect():
                if self.bt_manager.connect(port):
                    self.root.after(0, self._sync_settings_to_esp32)
                else:
                    self.root.after(0, lambda: self.status_var.set("Auto-connect failed"))

            threading.Thread(target=connect, daemon=True).start()

    def _sync_settings_to_esp32(self):
        if not self.bt_manager.is_connected():
            return

        self.bt_manager.send_command(CommandProtocol.set_type(self.settings.actuator_type))
        self.bt_manager.send_command(CommandProtocol.set_extend(self.settings.extend_offset))
        self.bt_manager.send_command(CommandProtocol.set_retract(self.settings.retract_offset))
        self.bt_manager.send_command(CommandProtocol.set_dwell_extend(self.settings.dwell_extend_ms))
        self.bt_manager.send_command(CommandProtocol.set_dwell_retract(self.settings.dwell_retract_ms))
        self.bt_manager.send_command(CommandProtocol.set_speed(self.settings.speed_percent))

        if self.infinite_cycles.get():
            self.bt_manager.send_command(CommandProtocol.set_cycles(0))
        else:
            self.bt_manager.send_command(CommandProtocol.set_cycles(self.cycles_var.get()))

    def _on_close(self):
        self.bt_manager.disconnect()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ActuatorControllerApp()
    app.run()

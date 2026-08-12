import sys
import os
import json
import logging
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QTextEdit, QDialog, QFormLayout, QLineEdit, QHeaderView, QFrame,
    QMessageBox, QSplitter
)
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

# Set up Qt Logging Signal
class WorkerSignals(QObject):
    log_message = Signal(str)
    status_changed = Signal(str)      # e.g., "Disconnected", "Discovered", "Registered", "Connected"
    metrics_updated = Signal(dict)    # cpu, ram, disk, temp, net_tx, net_rx, running_tasks
    task_started = Signal(dict)       # chunk_id, type
    task_completed = Signal(dict)     # chunk_id, status, duration
    master_info = Signal(str, int)    # ip, port

class QtLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CoCompute Agent Settings")
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e24;
                color: #ffffff;
            }
            QLabel {
                color: #a0a0b0;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #2b2b36;
                border: 1px solid #3f3f50;
                border-radius: 6px;
                padding: 6px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton#cancelBtn {
                background-color: #3f3f50;
            }
            QPushButton#cancelBtn:hover {
                background-color: #4b4b5f;
            }
        """)

        layout = QFormLayout(self)
        
        self.ip_edit = QLineEdit(os.getenv("MASTER_IP", ""))
        self.ip_edit.setPlaceholderText("Auto-discover (Leave blank)")
        self.port_edit = QLineEdit(os.getenv("MASTER_PORT", ""))
        self.port_edit.setPlaceholderText("Auto-discover (Leave blank)")
        self.key_edit = QLineEdit(os.getenv("WORKER_API_KEY", "cocompute-worker-key"))
        self.interval_edit = QLineEdit(os.getenv("HEARTBEAT_INTERVAL", "5"))

        layout.addRow("Master IP:", self.ip_edit)
        layout.addRow("Master Port:", self.port_edit)
        layout.addRow("API Key:", self.key_edit)
        layout.addRow("Heartbeat Interval (s):", self.interval_edit)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)

    def get_settings(self):
        return {
            "MASTER_IP": self.ip_edit.text().strip(),
            "MASTER_PORT": self.port_edit.text().strip(),
            "WORKER_API_KEY": self.key_edit.text().strip(),
            "HEARTBEAT_INTERVAL": self.interval_edit.text().strip()
        }


class MainWindow(QMainWindow):
    def __init__(self, stop_callback=None, start_callback=None):
        super().__init__()
        self.stop_callback = stop_callback
        self.start_callback = start_callback
        self.is_connected = False
        
        self.setWindowTitle("CoCompute Worker Agent Dashboard")
        self.resize(950, 680)
        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ─── HEADER PANEL ───
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title_lbl = QLabel("⚡ CoCompute Worker Agent")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        
        self.status_badge = QLabel("DISCONNECTED")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.setStyleSheet("""
            QLabel#StatusBadge {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 10px;
            }
        """)

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        main_layout.addWidget(header_frame)

        # Splitter for Main layout
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # ─── TOP AREA: INFO & METRICS (horizontal layout inside a widget) ───
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        # Connection / HW specs info panel
        info_frame = QFrame()
        info_frame.setObjectName("CardFrame")
        info_layout = QFormLayout(info_frame)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        self.master_lbl = QLabel("ws://localhost:8000")
        self.worker_uid_lbl = QLabel(os.getenv("WORKER_UID", "Unknown"))
        self.cpu_model_lbl = QLabel("Unknown CPU")
        self.os_lbl = QLabel("Unknown OS")
        self.agent_ver_lbl = QLabel("1.0.0")

        info_layout.addRow("Master Host:", self.master_lbl)
        info_layout.addRow("Worker ID:", self.worker_uid_lbl)
        info_layout.addRow("Processor:", self.cpu_model_lbl)
        info_layout.addRow("Operating System:", self.os_lbl)
        info_layout.addRow("Agent Version:", self.agent_ver_lbl)

        # Real-time hardware progress bars panel
        hw_frame = QFrame()
        hw_frame.setObjectName("CardFrame")
        hw_layout = QVBoxLayout(hw_frame)
        hw_layout.setContentsMargins(15, 15, 15, 15)
        hw_layout.setSpacing(8)

        # CPU utilization bar
        cpu_lbl_layout = QHBoxLayout()
        cpu_lbl_layout.addWidget(QLabel("CPU Utilization:"))
        self.cpu_val_lbl = QLabel("0%")
        self.cpu_val_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
        cpu_lbl_layout.addStretch()
        cpu_lbl_layout.addWidget(self.cpu_val_lbl)
        hw_layout.addLayout(cpu_lbl_layout)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setTextVisible(False)
        hw_layout.addWidget(self.cpu_bar)

        # RAM utilization bar
        ram_lbl_layout = QHBoxLayout()
        ram_lbl_layout.addWidget(QLabel("RAM Usage:"))
        self.ram_val_lbl = QLabel("0%")
        self.ram_val_lbl.setStyleSheet("font-weight: bold; color: #8b5cf6;")
        ram_lbl_layout.addStretch()
        ram_lbl_layout.addWidget(self.ram_val_lbl)
        hw_layout.addLayout(ram_lbl_layout)
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setValue(0)
        self.ram_bar.setTextVisible(False)
        self.ram_bar.setStyleSheet("QProgressBar::chunk { background-color: #8b5cf6; }")
        hw_layout.addWidget(self.ram_bar)

        # Disk utilization bar
        disk_lbl_layout = QHBoxLayout()
        disk_lbl_layout.addWidget(QLabel("Disk Space Usage:"))
        self.disk_val_lbl = QLabel("0%")
        self.disk_val_lbl.setStyleSheet("font-weight: bold; color: #10b981;")
        disk_lbl_layout.addStretch()
        disk_lbl_layout.addWidget(self.disk_val_lbl)
        hw_layout.addLayout(disk_lbl_layout)
        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        self.disk_bar.setValue(0)
        self.disk_bar.setTextVisible(False)
        self.disk_bar.setStyleSheet("QProgressBar::chunk { background-color: #10b981; }")
        hw_layout.addWidget(self.disk_bar)

        # Task detail summary layout inside hardware frame
        hw_detail_layout = QHBoxLayout()
        self.tasks_completed_lbl = QLabel("Completed: 0")
        self.tasks_failed_lbl = QLabel("Failed: 0")
        self.running_tasks_lbl = QLabel("Active: 0")
        self.reliability_lbl = QLabel("Reliability: 100%")
        
        self.tasks_completed_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        self.tasks_failed_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        self.running_tasks_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        self.reliability_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px; font-weight: bold;")

        hw_detail_layout.addWidget(self.running_tasks_lbl)
        hw_detail_layout.addWidget(self.tasks_completed_lbl)
        hw_detail_layout.addWidget(self.tasks_failed_lbl)
        hw_detail_layout.addWidget(self.reliability_lbl)
        hw_layout.addLayout(hw_detail_layout)

        top_layout.addWidget(info_frame, 2)
        top_layout.addWidget(hw_frame, 3)
        
        # Add top area to splitter
        splitter.addWidget(top_widget)

        # ─── MIDDLE AREA: RUNNING TASK & CONTROLS ───
        mid_widget = QWidget()
        mid_layout = QHBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(12)

        # Current running task details
        task_frame = QFrame()
        task_frame.setObjectName("CardFrame")
        task_layout = QVBoxLayout(task_frame)
        task_layout.setContentsMargins(15, 12, 15, 12)
        
        task_title = QLabel("Current Task Status")
        task_title.setStyleSheet("font-weight: bold; color: #a0a0b0; font-size: 12px;")
        task_layout.addWidget(task_title)

        self.curr_task_lbl = QLabel("Idle - Waiting for computation from Master Node")
        self.curr_task_lbl.setStyleSheet("font-size: 14px; color: #e4e4e7; font-weight: 500;")
        task_layout.addWidget(self.curr_task_lbl)
        
        self.curr_task_progress = QProgressBar()
        self.curr_task_progress.setRange(0, 100)
        self.curr_task_progress.setValue(0)
        self.curr_task_progress.setFixedHeight(12)
        task_layout.addWidget(self.curr_task_progress)

        # Toolbar controls panel
        control_frame = QFrame()
        control_frame.setObjectName("CardFrame")
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(12, 12, 12, 12)
        control_layout.setSpacing(8)

        self.connect_btn = QPushButton("Disconnect Agent")
        self.connect_btn.setObjectName("ConnectBtn")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        
        refresh_btn = QPushButton("Refresh History")
        refresh_btn.clicked.connect(self.refresh_history)

        control_layout.addWidget(self.connect_btn)
        control_layout.addWidget(settings_btn)
        control_layout.addWidget(refresh_btn)

        mid_layout.addWidget(task_frame, 4)
        mid_layout.addWidget(control_frame, 1)
        
        # Add middle area to splitter
        splitter.addWidget(mid_widget)

        # ─── BOTTOM AREA: HISTORY & LOGS (horizontal splitter) ───
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        # Task history table
        hist_frame = QFrame()
        hist_frame.setObjectName("CardFrame")
        hist_layout = QVBoxLayout(hist_frame)
        hist_layout.setContentsMargins(10, 10, 10, 10)
        hist_layout.addWidget(QLabel("Local Execution History (task_history.db)"))
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Chunk ID", "Status", "Duration (s)", "Timestamp"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setStyleSheet("QTableWidget { background-color: #111115; border: none; gridline-color: #2b2b36; }")
        hist_layout.addWidget(self.history_table)

        # Console logging text window
        log_frame = QFrame()
        log_frame.setObjectName("CardFrame")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.addWidget(QLabel("Live System Logs"))
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("QTextEdit { background-color: #0b0b0f; border: none; color: #a3e635; }")
        log_layout.addWidget(self.log_text)

        bottom_layout.addWidget(hist_frame, 3)
        bottom_layout.addWidget(log_frame, 2)
        
        # Add bottom area to splitter
        splitter.addWidget(bottom_widget)

        # Set stretch factor
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 4)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111115;
            }
            QFrame#HeaderFrame {
                background-color: #1e1e24;
                border: 1px solid #2b2b36;
                border-radius: 8px;
            }
            QFrame#CardFrame {
                background-color: #18181c;
                border: 1px solid #23232c;
                border-radius: 8px;
            }
            QLabel {
                color: #e4e4e7;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QProgressBar {
                background-color: #23232c;
                border: 1px solid #2b2b36;
                border-radius: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #23232c;
                color: #e4e4e7;
                border: 1px solid #3f3f50;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2b2b36;
                border: 1px solid #52526b;
            }
            QPushButton#ConnectBtn {
                background-color: #dc2626;
                border: 1px solid #ef4444;
                color: white;
                font-weight: bold;
            }
            QPushButton#ConnectBtn:hover {
                background-color: #b91c1c;
            }
        """)

    @Slot(str)
    def update_status(self, status):
        self.status_badge.setText(status.upper())
        if status.lower() == "connected" or status.lower() == "registered":
            self.status_badge.setStyleSheet("""
                QLabel#StatusBadge {
                    background-color: #10b981;
                    color: white;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 4px 10px;
                    border-radius: 10px;
                }
            """)
            self.connect_btn.setText("Disconnect Agent")
            self.connect_btn.setStyleSheet("""
                QPushButton#ConnectBtn {
                    background-color: #dc2626;
                    border: 1px solid #ef4444;
                    color: white;
                    font-weight: bold;
                }
                QPushButton#ConnectBtn:hover {
                    background-color: #b91c1c;
                }
            """)
            self.is_connected = True
        else:
            color = "#ef4444"
            if status.lower() in ("discovered", "connecting"):
                color = "#f59e0b"
            self.status_badge.setStyleSheet(f"""
                QLabel#StatusBadge {{
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 4px 10px;
                    border-radius: 10px;
                }}
            """)
            self.connect_btn.setText("Connect Agent")
            self.connect_btn.setStyleSheet("""
                QPushButton#ConnectBtn {
                    background-color: #10b981;
                    border: 1px solid #34d399;
                    color: white;
                    font-weight: bold;
                }
                QPushButton#ConnectBtn:hover {
                    background-color: #059669;
                }
            """)
            self.is_connected = False

    @Slot(dict)
    def update_metrics(self, data):
        self.cpu_bar.setValue(int(data.get("cpu_usage", 0)))
        self.cpu_val_lbl.setText(f"{data.get('cpu_usage', 0):.1f}%")
        
        self.ram_bar.setValue(int(data.get("ram_usage", 0)))
        self.ram_val_lbl.setText(f"{data.get('ram_usage', 0):.1f}%")
        
        self.disk_bar.setValue(int(data.get("disk_usage", 0)))
        self.disk_val_lbl.setText(f"{data.get('disk_usage', 0):.1f}%")

        self.running_tasks_lbl.setText(f"Active: {data.get('running_tasks', 0)}")
        
        # Load details from local history
        from ..history.task_history import get_task_stats
        stats = get_task_stats()
        self.tasks_completed_lbl.setText(f"Completed: {stats.get('completed', 0)}")
        self.tasks_failed_lbl.setText(f"Failed: {stats.get('failed', 0)}")
        
        total = stats.get('total_tasks', 0)
        rel = (stats.get('completed', 0) / total * 100) if total > 0 else 100.0
        self.reliability_lbl.setText(f"Reliability: {rel:.1f}%")

    @Slot(dict)
    def handle_task_started(self, data):
        self.curr_task_lbl.setText(f"Executing Chunk {data.get('chunk_id')} ({data.get('type')})")
        self.curr_task_progress.setRange(0, 0) # Indeterminate spinner
        self.curr_task_progress.setValue(0)

    @Slot(dict)
    def handle_task_completed(self, data):
        self.curr_task_lbl.setText(f"Idle - Waiting for computation from Master Node")
        self.curr_task_progress.setRange(0, 100)
        self.curr_task_progress.setValue(0)
        self.refresh_history()

    @Slot(str, int)
    def update_master_info(self, ip, port):
        self.master_lbl.setText(f"ws://{ip}:{port}")
        from ..monitor.metrics import get_hardware_info
        hw = get_hardware_info()
        self.cpu_model_lbl.setText(hw.get("cpu_model", "Unknown"))
        self.os_lbl.setText(hw.get("platform", "Unknown"))
        self.worker_uid_lbl.setText(hw.get("worker_uid", os.getenv("WORKER_UID", "Unknown")))

    @Slot(str)
    def append_log(self, message):
        self.log_text.append(message)
        # Scroll to bottom
        self.log_text.ensureCursorVisible()

    def toggle_connection(self):
        if self.is_connected:
            if self.stop_callback:
                self.stop_callback()
            self.update_status("disconnected")
            self.append_log("[UI] Disconnect requested by user.")
        else:
            self.update_status("connecting")
            if self.start_callback:
                self.start_callback()
            self.append_log("[UI] Connect requested by user.")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            for k, v in settings.items():
                if v:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)
            
            self.append_log("[UI] Settings saved. Reconnecting with new configuration...")
            # Cycle connection to apply new environment variables
            if self.is_connected:
                self.toggle_connection() # Disconnect
            self.toggle_connection() # Connect

    def refresh_history(self):
        from ..history.task_history import get_task_history
        history = get_task_history(limit=50)
        
        self.history_table.setRowCount(0)
        for row, item in enumerate(history):
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(str(item["chunk_id"])))
            
            status_item = QTableWidgetItem(item["status"].upper())
            if item["status"].lower() == "success" or item["status"].lower() == "completed":
                status_item.setForeground(QColor("#10b981"))
            else:
                status_item.setForeground(QColor("#ef4444"))
            self.history_table.setItem(row, 1, status_item)
            
            exec_time = f"{item['execution_time_seconds']:.3f}" if item['execution_time_seconds'] is not None else "—"
            self.history_table.setItem(row, 2, QTableWidgetItem(exec_time))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(item["created_at"])))

        # Update aggregated labels
        from ..history.task_history import get_task_stats
        stats = get_task_stats()
        self.tasks_completed_lbl.setText(f"Completed: {stats.get('completed', 0)}")
        self.tasks_failed_lbl.setText(f"Failed: {stats.get('failed', 0)}")


# Application runner helper
def run_qt_app(signals_obj, stop_cb, start_cb):
    app = QApplication(sys.argv)
    
    # Palette styling for native dialogs
    app.setStyle('Fusion')
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(17, 17, 21))
    dark_palette.setColor(QPalette.WindowText, QColor(228, 228, 231))
    dark_palette.setColor(QPalette.Base, QColor(11, 11, 15))
    dark_palette.setColor(QPalette.AlternateBase, QColor(24, 24, 28))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, QColor(228, 228, 231))
    dark_palette.setColor(QPalette.Button, QColor(35, 35, 44))
    dark_palette.setColor(QPalette.ButtonText, QColor(228, 228, 231))
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(59, 130, 246))
    dark_palette.setColor(QPalette.Highlight, QColor(59, 130, 246))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    window = MainWindow(stop_callback=stop_cb, start_callback=start_cb)
    
    # Connect Signals to Main Window slots
    signals_obj.log_message.connect(window.append_log)
    signals_obj.status_changed.connect(window.update_status)
    signals_obj.metrics_updated.connect(window.update_metrics)
    signals_obj.task_started.connect(window.handle_task_started)
    signals_obj.task_completed.connect(window.handle_task_completed)
    signals_obj.master_info.connect(window.update_master_info)

    # Attach logger handler
    handler = QtLogHandler(signals_obj.log_message)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(handler)

    # Initial history populate
    window.refresh_history()

    # Get original master info if set in env
    master_ip = os.getenv("MASTER_IP")
    master_port = os.getenv("MASTER_PORT")
    if master_ip and master_port:
        window.update_master_info(master_ip, int(master_port))

    window.show()
    sys.exit(app.exec())

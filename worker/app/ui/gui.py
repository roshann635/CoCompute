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
    QMessageBox, QSplitter, QSpinBox
)
from PySide6.QtGui import QFont, QColor, QPalette, QIcon


class WorkerSignals(QObject):
    log_message = Signal(str)
    status_changed = Signal(str)
    metrics_updated = Signal(dict)
    task_started = Signal(dict)
    task_completed = Signal(dict)
    master_info = Signal(str, int)


class QtLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class TaskDetailDialog(QDialog):
    """
    Task History drill-down dialog (Section 8 of Master Prompt).
    Displays: Job ID, Chunk ID, Operation, Start/End times, Duration, Status, and Result/Error.
    """
    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Chunk Details — CHUNK-{item_data.get('chunk_id')}")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: #ffffff; }
            QLabel { color: #a0a0b0; font-size: 12px; font-weight: bold; }
            QLineEdit, QTextEdit {
                background-color: #2b2b36; border: 1px solid #3f3f50;
                border-radius: 6px; padding: 6px; color: #ffffff; font-size: 12px;
            }
            QPushButton {
                background-color: #3b82f6; color: white; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; font-size: 12px;
            }
        """)

        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        chunk_id_edit = QLineEdit(str(item_data.get("chunk_id", "—")))
        chunk_id_edit.setReadOnly(True)
        layout.addRow("Chunk ID:", chunk_id_edit)

        status_edit = QLineEdit(str(item_data.get("status", "—")).upper())
        status_edit.setReadOnly(True)
        status_color = "#10b981" if item_data.get("status") in ("success", "completed") else "#ef4444"
        status_edit.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        layout.addRow("Status:", status_edit)

        exec_time = f"{item_data.get('execution_time_seconds', 0):.4f} seconds" if item_data.get('execution_time_seconds') is not None else "—"
        exec_edit = QLineEdit(exec_time)
        exec_edit.setReadOnly(True)
        layout.addRow("Duration:", exec_edit)

        start_edit = QLineEdit(str(item_data.get("start_time") or "—"))
        start_edit.setReadOnly(True)
        layout.addRow("Start Time:", start_edit)

        end_edit = QLineEdit(str(item_data.get("end_time") or "—"))
        end_edit.setReadOnly(True)
        layout.addRow("End Time:", end_edit)

        res_text = QTextEdit()
        res_text.setReadOnly(True)
        summary = item_data.get("result_summary") or item_data.get("error_message") or "No result data"
        res_text.setText(str(summary))
        res_text.setFixedHeight(120)
        layout.addRow("Result / Error:", res_text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addRow(close_btn)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CoCompute Agent Settings")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: #ffffff; }
            QLabel { color: #a0a0b0; font-size: 12px; font-weight: bold; }
            QLabel#ReadOnlyInfo { color: #6b7280; font-size: 10px; font-weight: normal; font-style: italic; }
            QLineEdit, QSpinBox {
                background-color: #2b2b36; border: 1px solid #3f3f50;
                border-radius: 6px; padding: 6px; color: #ffffff; font-size: 12px;
            }
            QPushButton {
                background-color: #3b82f6; color: white; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; font-size: 12px;
            }
            QPushButton#cancelBtn { background-color: #3f3f50; }
        """)

        layout = QFormLayout(self)
        self.worker_id_display = QLineEdit(os.getenv("WORKER_UID", "Auto-assigned"))
        self.worker_id_display.setReadOnly(True)
        layout.addRow("Worker ID:", self.worker_id_display)

        self.master_display = QLineEdit(
            f"{os.getenv('MASTER_IP', 'Auto-discover')}:{os.getenv('MASTER_PORT', '')}"
        )
        self.master_display.setReadOnly(True)
        layout.addRow("Master:", self.master_display)

        info_label = QLabel("☝ Worker ID and Master are auto-assigned via UDP discovery.")
        info_label.setObjectName("ReadOnlyInfo")
        layout.addRow(info_label)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(int(os.getenv("HEARTBEAT_INTERVAL", "5")))
        self.interval_spin.setSuffix(" seconds")
        layout.addRow("Heartbeat Interval:", self.interval_spin)

        self.key_edit = QLineEdit(os.getenv("WORKER_API_KEY", "cocompute-worker-key"))
        layout.addRow("API Key / Token:", self.key_edit)

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
            "HEARTBEAT_INTERVAL": str(self.interval_spin.value()),
            "WORKER_API_KEY": self.key_edit.text().strip(),
        }


class MainWindow(QMainWindow):
    def __init__(self, stop_callback=None, start_callback=None):
        super().__init__()
        self.stop_callback = stop_callback
        self.start_callback = start_callback
        self.is_connected = False
        self._current_chunk_uid = None
        self._history_cache = []

        self.setWindowTitle("CoCompute Worker Agent Dashboard")
        self.resize(980, 750)
        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ─── HEADER PANEL ───
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title_lbl = QLabel("⚡ CoCompute Worker Agent")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")

        self.status_badge = QLabel("DISCONNECTED")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.setStyleSheet("""
            QLabel#StatusBadge {
                background-color: #ef4444; color: white; font-weight: bold;
                font-size: 11px; padding: 4px 10px; border-radius: 10px;
            }
        """)

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        main_layout.addWidget(header_frame)

        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # ─── TOP AREA: SPECS & HARDWARE GAUGES ───
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        info_frame = QFrame()
        info_frame.setObjectName("CardFrame")
        info_layout = QFormLayout(info_frame)
        info_layout.setContentsMargins(15, 15, 15, 15)

        self.master_lbl = QLabel("ws://localhost:8000")
        self.master_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.worker_uid_lbl = QLabel(os.getenv("WORKER_UID", "Unknown"))
        self.worker_uid_lbl.setStyleSheet("font-weight: bold; color: #3b82f6; font-size: 12px;")
        self.cpu_model_lbl = QLabel("Detecting CPU...")
        self.cpu_model_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        self.gpu_model_lbl = QLabel("Checking GPU...")
        self.gpu_model_lbl.setStyleSheet("color: #10b981; font-size: 11px;")
        self.os_lbl = QLabel("Detecting OS...")
        self.os_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")

        info_layout.addRow("Master Host:", self.master_lbl)
        info_layout.addRow("Worker ID:", self.worker_uid_lbl)
        info_layout.addRow("CPU:", self.cpu_model_lbl)
        info_layout.addRow("GPU:", self.gpu_model_lbl)
        info_layout.addRow("OS:", self.os_lbl)

        # Hardware Utilization Bars
        hw_frame = QFrame()
        hw_frame.setObjectName("CardFrame")
        hw_layout = QVBoxLayout(hw_frame)
        hw_layout.setContentsMargins(15, 15, 15, 15)
        hw_layout.setSpacing(6)

        # CPU
        cpu_l = QHBoxLayout()
        cpu_l.addWidget(QLabel("CPU:"))
        self.cpu_val_lbl = QLabel("0%")
        self.cpu_val_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
        cpu_l.addStretch()
        cpu_l.addWidget(self.cpu_val_lbl)
        hw_layout.addLayout(cpu_l)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setTextVisible(False)
        hw_layout.addWidget(self.cpu_bar)

        # RAM
        ram_l = QHBoxLayout()
        ram_l.addWidget(QLabel("RAM:"))
        self.ram_val_lbl = QLabel("0%")
        self.ram_val_lbl.setStyleSheet("font-weight: bold; color: #8b5cf6;")
        ram_l.addStretch()
        ram_l.addWidget(self.ram_val_lbl)
        hw_layout.addLayout(ram_l)
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setValue(0)
        self.ram_bar.setTextVisible(False)
        self.ram_bar.setStyleSheet("QProgressBar::chunk { background-color: #8b5cf6; }")
        hw_layout.addWidget(self.ram_bar)

        # GPU / VRAM
        gpu_l = QHBoxLayout()
        gpu_l.addWidget(QLabel("GPU / VRAM:"))
        self.gpu_val_lbl = QLabel("0%")
        self.gpu_val_lbl.setStyleSheet("font-weight: bold; color: #10b981;")
        gpu_l.addStretch()
        gpu_l.addWidget(self.gpu_val_lbl)
        hw_layout.addLayout(gpu_l)
        self.gpu_bar = QProgressBar()
        self.gpu_bar.setRange(0, 100)
        self.gpu_bar.setValue(0)
        self.gpu_bar.setTextVisible(False)
        self.gpu_bar.setStyleSheet("QProgressBar::chunk { background-color: #10b981; }")
        hw_layout.addWidget(self.gpu_bar)

        top_layout.addWidget(info_frame, 2)
        top_layout.addWidget(hw_frame, 3)
        splitter.addWidget(top_widget)

        # ─── MIDDLE AREA: CURRENT TASK & CONTROLS ───
        mid_widget = QWidget()
        mid_layout = QHBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(12)

        task_frame = QFrame()
        task_frame.setObjectName("CardFrame")
        task_layout = QVBoxLayout(task_frame)
        task_layout.setContentsMargins(15, 12, 15, 12)

        task_title = QLabel("Current Task Status")
        task_title.setStyleSheet("font-weight: bold; color: #a0a0b0; font-size: 12px;")
        task_layout.addWidget(task_title)

        self.curr_task_lbl = QLabel("Idle — Waiting for computation from Master Node")
        self.curr_task_lbl.setStyleSheet("font-size: 13px; color: #e4e4e7; font-weight: 500;")
        task_layout.addWidget(self.curr_task_lbl)

        id_layout = QHBoxLayout()
        self.job_uid_lbl = QLabel("Job: —")
        self.job_uid_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.chunk_uid_lbl = QLabel("Chunk: —")
        self.chunk_uid_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        self.last_result_lbl = QLabel("Last Result: —")
        self.last_result_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        id_layout.addWidget(self.job_uid_lbl)
        id_layout.addWidget(self.chunk_uid_lbl)
        id_layout.addStretch()
        id_layout.addWidget(self.last_result_lbl)
        task_layout.addLayout(id_layout)

        self.curr_task_progress = QProgressBar()
        self.curr_task_progress.setRange(0, 100)
        self.curr_task_progress.setValue(0)
        self.curr_task_progress.setFixedHeight(10)
        task_layout.addWidget(self.curr_task_progress)

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
        splitter.addWidget(mid_widget)

        # ─── BOTTOM AREA: TASK HISTORY TABLE & LOGS ───
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        hist_frame = QFrame()
        hist_frame.setObjectName("CardFrame")
        hist_layout = QVBoxLayout(hist_frame)
        hist_layout.setContentsMargins(10, 10, 10, 10)
        hist_title = QLabel("Execution History (Click row for full drill-down)")
        hist_title.setStyleSheet("font-weight: bold; color: #a0a0b0; font-size: 11px;")
        hist_layout.addWidget(hist_title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Chunk ID", "Status", "Duration (s)", "Timestamp"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.cellDoubleClicked.connect(self.on_history_row_clicked)
        self.history_table.cellClicked.connect(self.on_history_row_clicked)
        self.history_table.setStyleSheet("QTableWidget { background-color: #111115; border: none; gridline-color: #2b2b36; }")
        hist_layout.addWidget(self.history_table)

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
        splitter.addWidget(bottom_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 4)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #111115; }
            QFrame#HeaderFrame { background-color: #1e1e24; border: 1px solid #2b2b36; border-radius: 8px; }
            QFrame#CardFrame { background-color: #18181c; border: 1px solid #23232c; border-radius: 8px; }
            QLabel { color: #e4e4e7; font-family: 'Segoe UI', Arial, sans-serif; }
            QProgressBar { background-color: #23232c; border: 1px solid #2b2b36; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background-color: #3b82f6; border-radius: 5px; }
            QPushButton { background-color: #23232c; color: #e4e4e7; border: 1px solid #3f3f50; border-radius: 6px; padding: 6px 12px; font-weight: 500; }
            QPushButton:hover { background-color: #2b2b36; border: 1px solid #52526b; }
            QPushButton#ConnectBtn { background-color: #dc2626; border: 1px solid #ef4444; color: white; font-weight: bold; }
            QPushButton#ConnectBtn:hover { background-color: #b91c1c; }
        """)

    @Slot(str)
    def update_status(self, status):
        self.status_badge.setText(status.upper())
        if status.lower() in ("connected", "registered"):
            self.status_badge.setStyleSheet("QLabel#StatusBadge { background-color: #10b981; color: white; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; }")
            self.connect_btn.setText("Disconnect Agent")
            self.connect_btn.setStyleSheet("QPushButton#ConnectBtn { background-color: #dc2626; border: 1px solid #ef4444; color: white; font-weight: bold; }")
            self.is_connected = True
        else:
            color = "#f59e0b" if status.lower() in ("discovered", "connecting", "busy") else "#ef4444"
            self.status_badge.setStyleSheet(f"QLabel#StatusBadge {{ background-color: {color}; color: white; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; }}")
            self.connect_btn.setText("Connect Agent")
            self.connect_btn.setStyleSheet("QPushButton#ConnectBtn { background-color: #10b981; border: 1px solid #34d399; color: white; font-weight: bold; }")
            self.is_connected = False

    @Slot(dict)
    def update_metrics(self, data):
        self.cpu_bar.setValue(int(data.get("cpu_usage", 0)))
        self.cpu_val_lbl.setText(f"{data.get('cpu_usage', 0):.1f}%")

        self.ram_bar.setValue(int(data.get("ram_usage", 0)))
        self.ram_val_lbl.setText(f"{data.get('ram_usage', 0):.1f}%")

        gpu_usage = data.get("gpu_utilization", 0.0) or 0.0
        self.gpu_bar.setValue(int(gpu_usage))
        self.gpu_val_lbl.setText(f"{gpu_usage:.1f}%")

    @Slot(dict)
    def handle_task_started(self, data):
        chunk_id = data.get('chunk_id')
        chunk_uid = data.get('chunk_uid', f'CHUNK-{chunk_id}')
        task_type = data.get('type', 'task')

        self.curr_task_lbl.setText(f"⚙ Executing {chunk_uid} ({task_type}) inside Docker container")
        self.chunk_uid_lbl.setText(f"Chunk: {chunk_uid}")
        self.curr_task_progress.setRange(0, 0)

    @Slot(dict)
    def handle_task_completed(self, data):
        status = data.get('status', 'unknown')
        if status in ('success', 'completed'):
            self.last_result_lbl.setText("Last Result: ✅ SUCCESS")
            self.last_result_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
        else:
            self.last_result_lbl.setText(f"Last Result: ❌ {status.upper()}")
            self.last_result_lbl.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: bold;")

        self.curr_task_lbl.setText("Idle — Waiting for computation from Master Node")
        self.chunk_uid_lbl.setText("Chunk: —")
        self.curr_task_progress.setRange(0, 100)
        self.curr_task_progress.setValue(0)
        self.refresh_history()

    @Slot(str, int)
    def update_master_info(self, ip, port):
        self.master_lbl.setText(f"ws://{ip}:{port}")
        from ..monitor.metrics import get_hardware_info
        hw = get_hardware_info()
        self.cpu_model_lbl.setText(hw.get("cpu_model", "Detected CPU"))
        self.gpu_model_lbl.setText(hw.get("gpu_model") or "No dedicated GPU (CPU mode)")
        self.os_lbl.setText(hw.get("platform", "Detected OS"))
        self.worker_uid_lbl.setText(hw.get("worker_uid", os.getenv("WORKER_UID", "Unknown")))

    @Slot(str)
    def append_log(self, message):
        self.log_text.append(message)
        self.log_text.ensureCursorVisible()

    def on_history_row_clicked(self, row: int, col: int = 0):
        if row < len(self._history_cache):
            item_data = self._history_cache[row]
            dialog = TaskDetailDialog(item_data, self)
            dialog.exec()

    def toggle_connection(self):
        if self.is_connected:
            if self.stop_callback:
                self.stop_callback()
            self.update_status("disconnected")
        else:
            self.update_status("connecting")
            if self.start_callback:
                self.start_callback()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            for k, v in settings.items():
                if v:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)
            if self.is_connected:
                self.toggle_connection()
            self.toggle_connection()

    def refresh_history(self):
        from ..history.task_history import get_task_history
        self._history_cache = get_task_history(limit=50)

        self.history_table.setRowCount(0)
        for row, item in enumerate(self._history_cache):
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(f"CHUNK-{item['chunk_id']}"))

            status_item = QTableWidgetItem(item["status"].upper())
            if item["status"].lower() in ("success", "completed"):
                status_item.setForeground(QColor("#10b981"))
            else:
                status_item.setForeground(QColor("#ef4444"))
            self.history_table.setItem(row, 1, status_item)

            exec_time = f"{item['execution_time_seconds']:.3f}" if item['execution_time_seconds'] is not None else "—"
            self.history_table.setItem(row, 2, QTableWidgetItem(exec_time))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(item["created_at"])))


def run_qt_app(signals_obj, stop_cb, start_cb):
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(17, 17, 21))
    dark_palette.setColor(QPalette.WindowText, QColor(228, 228, 231))
    dark_palette.setColor(QPalette.Base, QColor(11, 11, 15))
    dark_palette.setColor(QPalette.AlternateBase, QColor(24, 24, 28))
    dark_palette.setColor(QPalette.Button, QColor(35, 35, 44))
    dark_palette.setColor(QPalette.ButtonText, QColor(228, 228, 231))
    dark_palette.setColor(QPalette.Highlight, QColor(59, 130, 246))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    window = MainWindow(stop_callback=stop_cb, start_callback=start_cb)

    signals_obj.log_message.connect(window.append_log)
    signals_obj.status_changed.connect(window.update_status)
    signals_obj.metrics_updated.connect(window.update_metrics)
    signals_obj.task_started.connect(window.handle_task_started)
    signals_obj.task_completed.connect(window.handle_task_completed)
    signals_obj.master_info.connect(window.update_master_info)

    handler = QtLogHandler(signals_obj.log_message)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(handler)

    window.refresh_history()

    master_ip = os.getenv("MASTER_IP")
    master_port = os.getenv("MASTER_PORT")
    if master_ip and master_port:
        window.update_master_info(master_ip, int(master_port))

    window.show()
    sys.exit(app.exec())

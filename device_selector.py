import sys
import pyaudiowpatch as pyaudio
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

COMBO_STYLE = """
QComboBox {
    border: 1.5px solid #aaa;
    border-radius: 7px;
    padding: 5px 28px 5px 10px;
    font-size: 14px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f9fafd, stop:1 #e7e9f4);
}

QComboBox:focus {
    border-color: #8375e6;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eef1fa, stop:1 #e2d4f7);
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #bbb;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #edeaff, stop:1 #cdcaf2);
}

QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-top: 10px solid #8375e6;
    margin-right: 4px;
}

QComboBox QAbstractItemView {
    border: 2px solid #8375e6;
    background: #f3f7fb;
    selection-background-color: #edeaff;
    selection-color: #231264;
    font-size: 14px;
}
"""

class DeviceSelectionWindow(QWidget):
    devices_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device Selection")
        self.setFixedSize(600, 250)
        self.setStyleSheet("background: #fcfcfc; border-radius: 14px;")
        
        self.loopback_devices = []
        self.mic_devices = []
        self.populate_devices()
        self.initUI()

    def populate_devices(self):
        """Populate available audio devices"""
        p = pyaudio.PyAudio()
        
        # Find loopback devices
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0 and 'loopback' in info['name'].lower():
                self.loopback_devices.append((i, info))
        
        # If no loopback devices found, show all input devices
        if not self.loopback_devices:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    self.loopback_devices.append((i, info))
        
        # Find microphone devices
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0 and 'loopback' not in info['name'].lower():
                self.mic_devices.append((i, info))
        
        # If no mic devices found, show all input devices
        if not self.mic_devices:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    self.mic_devices.append((i, info))
        
        p.terminate()

    def initUI(self):
        # Title
        title = QLabel("⚙️ Device Selection")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        # Input Device panel (Loopback)
        input_label = QLabel("Loopback Device (Client Audio)")
        input_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        input_icon = QLabel("🔊")
        input_icon.setFont(QFont("Segoe UI Emoji", 22))
        self.input_combo = QComboBox()
        
        # Populate loopback devices
        for idx, (device_index, info) in enumerate(self.loopback_devices):
            self.input_combo.addItem(f"[{device_index}] {info['name']}")
        
        self.input_combo.setStyleSheet(COMBO_STYLE)
        self.input_combo.setFixedHeight(40)

        input_panel = QVBoxLayout()
        input_panel.addWidget(input_label)
        in_row = QHBoxLayout()
        in_row.addWidget(input_icon)
        in_row.addWidget(self.input_combo)
        in_row.setAlignment(Qt.AlignLeft)
        in_row.setSpacing(8)
        input_panel.addSpacing(2)
        input_panel.addLayout(in_row)

        # Output Device panel (Microphone)
        output_label = QLabel("Microphone Device (Your Audio)")
        output_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        output_icon = QLabel("🎤")
        output_icon.setFont(QFont("Segoe UI Emoji", 22))
        self.output_combo = QComboBox()
        
        # Populate microphone devices
        for idx, (device_index, info) in enumerate(self.mic_devices):
            self.output_combo.addItem(f"[{device_index}] {info['name']}")
        
        self.output_combo.setStyleSheet(COMBO_STYLE)
        self.output_combo.setFixedHeight(40)

        output_panel = QVBoxLayout()
        output_panel.addWidget(output_label)
        out_row = QHBoxLayout()
        out_row.addWidget(output_icon)
        out_row.addWidget(self.output_combo)
        out_row.setAlignment(Qt.AlignLeft)
        out_row.setSpacing(8)
        output_panel.addSpacing(2)
        output_panel.addLayout(out_row)

        # Devices side by side
        devices_layout = QHBoxLayout()
        devices_layout.addLayout(input_panel)
        devices_layout.addSpacing(40)
        devices_layout.addLayout(output_panel)
        devices_layout.addStretch()

        # Start button
        start_btn = QPushButton("Start")
        start_btn.setFixedWidth(110)
        start_btn.setFixedHeight(40)
        start_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        start_btn.setStyleSheet("""
            QPushButton {
                color: white;
                border: none;
                border-radius: 10px;
                background: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8375e6, stop:1 #d896e9
                );
            }
            QPushButton:hover {background-color: #7f8ce5;}
        """)
        start_btn.clicked.connect(self.on_start_clicked)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(title)
        main_layout.addSpacing(25)
        main_layout.addLayout(devices_layout)
        main_layout.addSpacing(24)
        main_layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        self.setLayout(main_layout)

    def on_start_clicked(self):
        """Handle start button click"""
        # Get selected devices
        loopback_idx = self.input_combo.currentIndex()
        mic_idx = self.output_combo.currentIndex()
        
        if loopback_idx >= 0 and mic_idx >= 0:
            loopback_index, loopback_info = self.loopback_devices[loopback_idx]
            mic_index, mic_info = self.mic_devices[mic_idx]
            
            device_info = {
                'loopback_index': loopback_index,
                'loopback_info': loopback_info,
                'mic_index': mic_index,
                'mic_info': mic_info
            }
            
            self.devices_selected.emit(device_info)
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceSelectionWindow()
    window.show()
    sys.exit(app.exec_())
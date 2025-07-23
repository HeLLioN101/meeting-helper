import sys
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QLineEdit, QFrame, QSplitter, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, pyqtSlot
try:
    from PyQt5.QtCore import QMetaType, QTextCursor
    QMetaType.type('QTextCursor')
except Exception:
    pass
from PyQt5.QtGui import QFont
from ai import get_chatbot_response
from PyPDF2 import PdfReader
from docx import Document
from pptx import Presentation
import os

class TranscriptionWorker(QObject):
    text_ready = pyqtSignal(str, str)
    
    def __init__(self, queue):
        super().__init__()
        self.running = False
        self.transcription_queue = queue
        
    def start_transcription(self):
        self.running = True
        self.monitor_queue()
    
    def stop_transcription(self):
        self.running = False
    
    def monitor_queue(self):
        def queue_monitor():
            while self.running:
                try:
                    if not self.transcription_queue.empty():
                        data = self.transcription_queue.get(timeout=0.1)
                        tag = data.get("tag", "unknown")
                        text = data.get("text", "")
                        
                        if text.strip():
                            self.text_ready.emit(text, tag)
                    
                    time.sleep(0.05)
                except:
                    time.sleep(0.1)
        
        thread = threading.Thread(target=queue_monitor)
        thread.daemon = True
        thread.start()

class CircularButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(80, 80)
        self.setStyleSheet("""
            QPushButton {
                border-radius: 40px;
                background-color: #E3F2FD;
                color: #1976D2;
                font-size: 24px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
            QPushButton:pressed {
                background-color: #90CAF9;
            }
        """)

class MainWindow(QMainWindow):
    def __init__(self, shared_queue):
        super().__init__()
        self.setWindowTitle("Live Transcription & AI Assistant")
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()  # Always open in full screen
        
        self.shared_queue = shared_queue
        self.last_uploaded_file_text = None  # Store last uploaded file text
        
        # Set up UI
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout(main_widget)
        main_layout.addWidget(splitter)
        
        left_panel = self.create_transcription_panel()
        right_panel = self.create_ai_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])
        
        self.setStyleSheet("QMainWindow { background-color: #F8FAFE; }")
        
        # Initialize transcription
        self.is_transcribing = False
        self.transcription_worker = TranscriptionWorker(self.shared_queue)
        self.transcription_worker.text_ready.connect(self.update_transcription)
        
        # Auto-start
        QTimer.singleShot(3000, self.auto_start_transcription)
    
    def auto_start_transcription(self):
        if not self.is_transcribing:
            self.start_transcription()
    
    def create_transcription_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                margin: 10px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        
        mic_icon = QLabel("🎤")
        mic_icon.setFont(QFont("Arial", 20))
        mic_icon.setStyleSheet("color: #1976D2;")
        
        title_layout = QVBoxLayout()
        title = QLabel("Live Transcription")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #333333;")
        
        subtitle = QLabel("Real-time speech-to-text")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #666666;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        header_layout.addWidget(mic_icon)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Transcription text area
        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #E3F2FD;
                border-radius: 10px;
                background-color: #FAFAFA;
                padding: 20px;
                font-size: 14px;
                line-height: 1.5;
                color: #333333;
                font-family: Arial, sans-serif;
                min-height: 400px;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #1976D2, stop:1 #90CAF9);
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.transcription_text.hide()
        layout.addWidget(self.transcription_text, stretch=6)
        
        # Center content
        layout.addStretch(0)
        
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setSpacing(15)
        
        self.mic_button = CircularButton("🎤")
        self.mic_button.clicked.connect(self.toggle_transcription)
        center_layout.addWidget(self.mic_button, alignment=Qt.AlignCenter)
        
        self.status_label = QLabel("Ready to transcribe")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: #333333;")
        self.status_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.status_label)
        
        self.instruction_label = QLabel('Auto-starting transcription in 3 seconds...')
        self.instruction_label.setFont(QFont("Arial", 12))
        self.instruction_label.setStyleSheet("color: #666666;")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.instruction_label)
        
        layout.addLayout(center_layout)
        layout.addStretch(0)
        
        # Stop button
        stop_layout = QHBoxLayout()
        self.stop_button = QPushButton("Stop Transcription")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 15px 30px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        self.stop_button.clicked.connect(self.stop_transcription)
        self.stop_button.hide()
        stop_layout.addStretch()
        stop_layout.addWidget(self.stop_button)
        stop_layout.addStretch()
        
        layout.addLayout(stop_layout)
        
        return panel
    
    def create_ai_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                margin: 10px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header_layout = QHBoxLayout()
        ai_icon = QLabel("✨")
        ai_icon.setFont(QFont("Arial", 20))
        ai_icon.setStyleSheet("color: #7C4DFF;")
        title_layout = QVBoxLayout()
        title = QLabel("AI Assistant")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #333333;")
        subtitle = QLabel("Intelligent meeting insights")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #666666;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addWidget(ai_icon)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Chat area
        self.ai_chat_area = QTextEdit()
        self.ai_chat_area.setReadOnly(True)
        self.ai_chat_area.setStyleSheet("""
            QTextEdit {
                border: 2px solid #E3F2FD;
                border-radius: 10px;
                background-color: #FAFAFA;
                padding: 20px;
                font-size: 15px;
                line-height: 2.0;
                color: #333333;
                font-family: Arial, sans-serif;
                min-height: 300px;
                margin-bottom: 10px;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #7C4DFF, stop:1 #BBDEFB);
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(self.ai_chat_area, stretch=2)

        # Input section
        input_layout = QVBoxLayout()
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Type your question for the AI...")
        self.ai_input.setFont(QFont("Arial", 12))
        self.ai_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 25px;
                padding: 15px 20px;
                font-size: 12px;
                background-color: #FAFAFA;
            }
            QLineEdit:focus {
                border-color: #7C4DFF;
                background-color: white;
            }
        """)
        button_layout = QHBoxLayout()
        upload_btn = QPushButton("📎 Upload")
        upload_btn.setFont(QFont("Arial", 10))
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #666666;
                padding: 10px;
            }
            QPushButton:hover {
                color: #7C4DFF;
            }
        """)
        button_layout.addWidget(upload_btn)
        button_layout.addStretch()
        ask_btn = QPushButton("Ask")
        ask_btn.setFont(QFont("Arial", 10))
        ask_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #666666;
                padding: 10px 15px;
            }
            QPushButton:hover {
                color: #7C4DFF;
            }
        """)
        send_btn = QPushButton("Send")
        send_btn.setFont(QFont("Arial", 10, QFont.Bold))
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #7C4DFF;
                color: white;
                border: none;
                border-radius: 15px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #6A3DE8;
            }
        """)
        button_layout.addWidget(ask_btn)
        button_layout.addWidget(send_btn)
        input_layout.addWidget(self.ai_input)
        input_layout.addLayout(button_layout)
        layout.addLayout(input_layout)

        upload_btn.clicked.connect(self.handle_upload_file)
        ask_btn.clicked.connect(self.handle_ai_send)
        send_btn.clicked.connect(self.handle_ai_send)
        self.ai_input.returnPressed.connect(self.handle_ai_send)  # Send on Enter
        return panel
    
    def toggle_transcription(self):
        if not self.is_transcribing:
            self.start_transcription()
        else:
            self.stop_transcription()
    
    def start_transcription(self):
        self.is_transcribing = True
        
        # Hide button elements
        self.mic_button.hide()
        self.status_label.hide()
        self.instruction_label.hide()
        
        # Show transcription elements
        self.transcription_text.show()
        self.stop_button.show()
        self.transcription_text.clear()
        
        self.transcription_text.append("🎤 Real-time transcription started... Listening for speech...")
        self.transcription_text.append("")
        
        # Start transcription worker
        self.transcription_worker.start_transcription()
    
    def stop_transcription(self):
        self.is_transcribing = False
        
        # Stop transcription worker
        self.transcription_worker.stop_transcription()
        
        # Hide transcription elements
        self.transcription_text.hide()
        self.stop_button.hide()
        
        # Show button elements
        self.mic_button.show()
        self.status_label.show()
        self.instruction_label.show()
        
        # Reset appearance
        self.mic_button.setText("🎤")
        self.status_label.setText("Ready to transcribe")
        self.status_label.setStyleSheet("color: #333333;")
        self.instruction_label.setText('Press "Start" to begin transcription')
    
    def update_transcription(self, new_text, tag):
        from PyQt5.QtCore import QTimer
        if self.is_transcribing:
            formatted_text = f"[{tag.upper()}] {new_text}"
            self.transcription_text.append(formatted_text)
            QTimer.singleShot(0, lambda: self.transcription_text.verticalScrollBar().setValue(self.transcription_text.verticalScrollBar().maximum()))

    def append_ai_message(self, text, sender="ai"):
        from PyQt5.QtCore import Qt, QTimer
        import re
        def markdown_to_html(md):
            html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', md)
            html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html)
            html = re.sub(r'\n(\d+)\. ', r'<br><b>\1.</b> ', html)
            html = re.sub(r'\n\* ', r'<br>&bull; ', html)
            html = html.replace('\n', '<br>')
            return html
        if sender == "user":
            self.ai_chat_area.append(f'<div style="margin-bottom:10px;"><b style="color:#1976D2;">You:</b> {text}</div>')
        else:
            formatted = markdown_to_html(text)
            self.ai_chat_area.append(f'<div style="margin-bottom:20px;"><b style="color:#7C4DFF;">AI:</b> {formatted}</div>')
            # Robust scroll to bottom only for AI response
            def scroll_to_bottom():
                bar = self.ai_chat_area.verticalScrollBar()
                bar.setValue(bar.maximum())
            QTimer.singleShot(0, scroll_to_bottom)
            QTimer.singleShot(50, scroll_to_bottom)
            QTimer.singleShot(100, scroll_to_bottom)
            QTimer.singleShot(200, scroll_to_bottom)
            QTimer.singleShot(400, scroll_to_bottom)
            QTimer.singleShot(800, scroll_to_bottom)

    @pyqtSlot()
    def handle_ai_send(self):
        user_text = self.ai_input.text()  # Removed .strip() to preserve all characters
        if not user_text:
            return
        self.append_ai_message(user_text, sender="user")
        self.ai_input.clear()
        # If file uploaded, prepend its content to the prompt
        if self.last_uploaded_file_text:
            prompt = f"File context:\n{self.last_uploaded_file_text}\n\nUser question: {user_text}"
        else:
            prompt = user_text
        threading.Thread(target=self.get_ai_response, args=(prompt,), daemon=True).start()

    def get_ai_response(self, user_text):
        self.append_ai_message("Thinking...", sender="ai")
        response = get_chatbot_response(user_text)
        # Remove the last "Thinking..." message
        cursor = self.ai_chat_area.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        self.ai_chat_area.setTextCursor(cursor)
        self.append_ai_message(response, sender="ai")

    def handle_upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a file", "", "Documents (*.pdf *.docx *.pptx)")
        if not file_path:
            return
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            elif ext == ".docx":
                doc = Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif ext == ".pptx":
                prs = Presentation(file_path)
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text += shape.text + "\n"
            else:
                self.append_ai_message("Unsupported file type.", sender="ai")
                return
        except Exception as e:
            self.append_ai_message(f"Error reading file: {e}", sender="ai")
            return
        if not text.strip():
            self.append_ai_message("No text found in the file.", sender="ai")
            return
        self.last_uploaded_file_text = text[:4000]  # Store up to 4000 chars for context
        self.append_ai_message(f"Uploaded file content. Summarizing...", sender="user")
        threading.Thread(target=self.get_ai_response, args=(f"Summarize this file:\n{text[:4000]}",), daemon=True).start()

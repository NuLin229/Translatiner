"""
FileSelector - File selection component for audio translator.

Implements file selection functionality with:
- File selection dialog for wav/mp3 files
- Display of supported file formats
- Display of selected file name
"""

import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.services.audio_processor import AudioProcessor


class FileSelector(QWidget):
    """
    File selection widget for audio files.
    
    Features:
    - File selection dialog (wav/mp3)
    - Display of supported formats
    - Display of selected file name
    
    Validates: Requirements 1.1, 7.1, 7.2
    """
    
    # Signal emitted when a file is selected
    file_selected = pyqtSignal(str)  # file_path
    
    # Supported file formats
    SUPPORTED_FORMATS = "音频文件 (*.wav *.mp3);;WAV 文件 (*.wav);;MP3 文件 (*.mp3)"
    SUPPORTED_EXTENSIONS = {'.wav', '.mp3'}
    
    def __init__(self, parent=None):
        """
        Initialize the file selector.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._selected_file: Optional[str] = None
        self._audio_processor = AudioProcessor()
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Container frame with border
        container = QFrame()
        container.setFrameShape(QFrame.Shape.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 2px dashed #CCCCCC;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #1DB954;
                background-color: #F0FFF4;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(10)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon/prompt label
        prompt_label = QLabel("🎵")
        prompt_label.setFont(QFont("Segoe UI Emoji", 32))
        prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(prompt_label)
        
        # Instruction text
        instruction_label = QLabel("点击选择音频文件")
        instruction_label.setFont(QFont("Microsoft YaHei", 14))
        instruction_label.setStyleSheet("color: #333333; font-weight: bold;")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(instruction_label)
        
        # Supported formats hint
        self.format_hint_label = QLabel("支持格式: wav / mp3")
        self.format_hint_label.setFont(QFont("Microsoft YaHei", 10))
        self.format_hint_label.setStyleSheet("color: #888888;")
        self.format_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.format_hint_label)
        
        # Select button
        self.select_button = QPushButton("选择文件")
        self.select_button.setMinimumWidth(120)
        self.select_button.setMinimumHeight(36)
        self.select_button.setFont(QFont("Microsoft YaHei", 11))
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        self.select_button.clicked.connect(self._on_select_clicked)
        container_layout.addWidget(self.select_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addWidget(container)
        
        # Selected file display area
        self.file_info_layout = QHBoxLayout()
        self.file_info_layout.setContentsMargins(5, 5, 5, 5)
        
        self.file_icon_label = QLabel("📁")
        self.file_icon_label.setFont(QFont("Segoe UI Emoji", 14))
        self.file_icon_label.setVisible(False)
        self.file_info_layout.addWidget(self.file_icon_label)
        
        self.file_name_label = QLabel("")
        self.file_name_label.setFont(QFont("Microsoft YaHei", 11))
        self.file_name_label.setStyleSheet("color: #333333;")
        self.file_name_label.setVisible(False)
        self.file_info_layout.addWidget(self.file_name_label)
        
        self.file_info_layout.addStretch(1)
        
        # Re-select button (shown after file is selected)
        self.reselect_button = QPushButton("重新选择")
        self.reselect_button.setFont(QFont("Microsoft YaHei", 10))
        self.reselect_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1DB954;
                border: 1px solid #1DB954;
                border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #E8F5E9;
            }
        """)
        self.reselect_button.setVisible(False)
        self.reselect_button.clicked.connect(self._on_select_clicked)
        self.file_info_layout.addWidget(self.reselect_button)
        
        main_layout.addLayout(self.file_info_layout)
    
    def _on_select_clicked(self):
        """Handle file selection button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            self.SUPPORTED_FORMATS
        )
        
        if file_path:
            self._set_selected_file(file_path)
    
    def _set_selected_file(self, file_path: str):
        """
        Set the selected file and update the UI.
        
        Args:
            file_path: Path to the selected file
        """
        # Validate file format
        if not self._audio_processor.is_supported_format(file_path):
            return
        
        self._selected_file = file_path
        
        # Update UI to show selected file
        file_name = os.path.basename(file_path)
        self.file_name_label.setText(file_name)
        self.file_name_label.setVisible(True)
        self.file_icon_label.setVisible(True)
        self.reselect_button.setVisible(True)
        
        # Emit signal
        self.file_selected.emit(file_path)
    
    @property
    def selected_file(self) -> Optional[str]:
        """Get the currently selected file path."""
        return self._selected_file
    
    def set_file(self, file_path: str):
        """
        Set the file programmatically.
        
        Args:
            file_path: Path to the audio file
        """
        if file_path and self._audio_processor.is_supported_format(file_path):
            self._set_selected_file(file_path)
    
    def clear_selection(self):
        """Clear the current file selection."""
        self._selected_file = None
        self.file_name_label.setText("")
        self.file_name_label.setVisible(False)
        self.file_icon_label.setVisible(False)
        self.reselect_button.setVisible(False)
    
    def get_file_name(self) -> Optional[str]:
        """
        Get the name of the selected file (without path).
        
        Returns:
            File name or None if no file is selected
        """
        if self._selected_file:
            return os.path.basename(self._selected_file)
        return None

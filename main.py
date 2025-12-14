"""
Audio Translator Application

A desktop application for translating audio files with:
- Support for wav and mp3 formats
- Speech recognition for Japanese, English, Korean, and Chinese
- Translation to target language
- NetEase Cloud Music style scrolling subtitles
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

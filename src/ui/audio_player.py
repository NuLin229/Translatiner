"""
AudioPlayer - Audio playback component for audio translator.

Implements audio playback functionality with:
- Play, pause, stop control buttons
- Playback progress synchronization with subtitles
"""

import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioPlayer(QWidget):
    """
    Audio playback widget with transport controls.
    
    Features:
    - Play, pause, stop buttons
    - Progress slider with time display
    - Playback position synchronization for subtitle sync
    
    Validates: Requirements 5.1, 5.2
    """
    
    # Signal emitted when playback position changes (for subtitle sync)
    position_changed = pyqtSignal(float)  # position in seconds
    
    # Signal emitted when playback state changes
    state_changed = pyqtSignal(str)  # 'playing', 'paused', 'stopped'
    
    # Signal emitted when playback finishes naturally (Requirements 6.1, 6.2)
    playback_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        """
        Initialize the audio player.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._duration: float = 0.0
        self._is_seeking = False
        self._setup_media_player()
        self._setup_ui()
        self._setup_timer()
    
    def _setup_media_player(self):
        """Set up the Qt media player."""
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        
        # Connect signals
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_error)
    
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Progress slider and time display
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        
        # Current time label
        self.current_time_label = QLabel("00:00:00")
        self.current_time_label.setFont(QFont("Microsoft YaHei", 10))
        self.current_time_label.setStyleSheet("color: #666666;")
        self.current_time_label.setMinimumWidth(60)
        progress_layout.addWidget(self.current_time_label)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)  # Use 1000 for smooth seeking
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #E0E0E0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ED760;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 2px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        progress_layout.addWidget(self.progress_slider, 1)
        
        # Total time label
        self.total_time_label = QLabel("00:00:00")
        self.total_time_label.setFont(QFont("Microsoft YaHei", 10))
        self.total_time_label.setStyleSheet("color: #666666;")
        self.total_time_label.setMinimumWidth(60)
        progress_layout.addWidget(self.total_time_label)
        
        main_layout.addLayout(progress_layout)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Stop button
        self.stop_button = QPushButton("⏹")
        self.stop_button.setFont(QFont("Segoe UI Emoji", 16))
        self.stop_button.setFixedSize(44, 44)
        self.stop_button.setStyleSheet(self._get_button_style())
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setToolTip("停止")
        controls_layout.addWidget(self.stop_button)
        
        # Play/Pause button
        self.play_pause_button = QPushButton("▶")
        self.play_pause_button.setFont(QFont("Segoe UI Emoji", 20))
        self.play_pause_button.setFixedSize(56, 56)
        self.play_pause_button.setStyleSheet(self._get_play_button_style())
        self.play_pause_button.clicked.connect(self._toggle_play_pause)
        self.play_pause_button.setToolTip("播放")
        controls_layout.addWidget(self.play_pause_button)
        
        # Placeholder for symmetry (could add more controls later)
        spacer = QWidget()
        spacer.setFixedSize(44, 44)
        controls_layout.addWidget(spacer)
        
        main_layout.addLayout(controls_layout)
        
        # Initially disable controls
        self._set_controls_enabled(False)
    
    def _get_button_style(self) -> str:
        """Get the style for control buttons."""
        return """
            QPushButton {
                background-color: #F0F0F0;
                border: none;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
            QPushButton:disabled {
                background-color: #F8F8F8;
                color: #CCCCCC;
            }
        """
    
    def _get_play_button_style(self) -> str:
        """Get the style for the play/pause button."""
        return """
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 28px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """
    
    def _setup_timer(self):
        """Set up the position update timer."""
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(100)  # Update every 100ms
        self._position_timer.timeout.connect(self._emit_position)
    
    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable playback controls."""
        self.play_pause_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.progress_slider.setEnabled(enabled)
    
    def load_file(self, file_path: str) -> bool:
        """
        Load an audio file for playback.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            True if file was loaded successfully
        """
        if not file_path or not os.path.exists(file_path):
            return False
        
        self.stop()
        self._player.setSource(QUrl.fromLocalFile(file_path))
        self._set_controls_enabled(True)
        return True
    
    def play(self):
        """Start or resume playback."""
        if self._player.source().isEmpty():
            return
        
        self._player.play()
        self._position_timer.start()
        self.play_pause_button.setText("⏸")
        self.play_pause_button.setToolTip("暂停")
    
    def pause(self):
        """Pause playback."""
        self._player.pause()
        self._position_timer.stop()
        self.play_pause_button.setText("▶")
        self.play_pause_button.setToolTip("播放")
    
    def stop(self):
        """Stop playback and reset position."""
        self._player.stop()
        self._position_timer.stop()
        self.play_pause_button.setText("▶")
        self.play_pause_button.setToolTip("播放")
        self.progress_slider.setValue(0)
        self.current_time_label.setText("00:00:00")
        self.position_changed.emit(0.0)
    
    def _toggle_play_pause(self):
        """Toggle between play and pause states."""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()
    
    def seek(self, position_seconds: float):
        """
        Seek to a specific position.
        
        Args:
            position_seconds: Position in seconds
        """
        position_ms = int(position_seconds * 1000)
        self._player.setPosition(position_ms)
        self.position_changed.emit(position_seconds)
    
    def _on_duration_changed(self, duration_ms: int):
        """Handle duration change from media player."""
        self._duration = duration_ms / 1000.0
        self.total_time_label.setText(self._format_time(self._duration))
    
    def _on_position_changed(self, position_ms: int):
        """Handle position change from media player."""
        if self._is_seeking:
            return
        
        position_seconds = position_ms / 1000.0
        self.current_time_label.setText(self._format_time(position_seconds))
        
        # Update slider
        if self._duration > 0:
            slider_value = int((position_seconds / self._duration) * 1000)
            self.progress_slider.setValue(slider_value)
    
    def _emit_position(self):
        """Emit the current position for subtitle synchronization."""
        if not self._is_seeking:
            position_seconds = self._player.position() / 1000.0
            self.position_changed.emit(position_seconds)
    
    def _on_state_changed(self, state: QMediaPlayer.PlaybackState):
        """Handle playback state change."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.state_changed.emit('playing')
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.state_changed.emit('paused')
        else:
            self.state_changed.emit('stopped')
    
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        """Handle media status change - detect end of playback."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Playback finished naturally (Requirements 6.1, 6.2)
            self._position_timer.stop()
            self.play_pause_button.setText("▶")
            self.play_pause_button.setToolTip("播放")
            self.playback_finished.emit()
    
    def _on_error(self, error: QMediaPlayer.Error, error_string: str):
        """Handle media player errors."""
        print(f"Audio player error: {error_string}")
    
    def _on_slider_pressed(self):
        """Handle slider press (start seeking)."""
        self._is_seeking = True
    
    def _on_slider_released(self):
        """Handle slider release (end seeking)."""
        self._is_seeking = False
        if self._duration > 0:
            position_seconds = (self.progress_slider.value() / 1000.0) * self._duration
            self.seek(position_seconds)
    
    def _on_slider_moved(self, value: int):
        """Handle slider movement during seeking."""
        if self._duration > 0:
            position_seconds = (value / 1000.0) * self._duration
            self.current_time_label.setText(self._format_time(position_seconds))
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        Format time in seconds to HH:MM:SS string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @property
    def duration(self) -> float:
        """Get the duration of the loaded audio in seconds."""
        return self._duration
    
    @property
    def position(self) -> float:
        """Get the current playback position in seconds."""
        return self._player.position() / 1000.0
    
    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
    
    def set_volume(self, volume: float):
        """
        Set the playback volume.
        
        Args:
            volume: Volume level from 0.0 to 1.0
        """
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

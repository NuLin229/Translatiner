"""
SubtitleView - NetEase Cloud Music style scrolling subtitle widget.

Implements a custom PyQt6 widget that displays subtitles with:
- Current sentence centered and highlighted
- Smooth scrolling animation
- Click-to-seek functionality
"""

from typing import Optional, List
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QMouseEvent

from src.services.subtitle_manager import SubtitleManager
from src.models.data_models import TranslationSegment


class SubtitleItemWidget(QWidget):
    """Individual subtitle item widget."""
    
    clicked = pyqtSignal(int, float)  # index, start_time
    
    # Style constants - consistent primary color #1DB954
    PRIMARY_COLOR = "#1DB954"
    TEXT_COLOR = "#333333"
    TEXT_SECONDARY = "#666666"
    TIME_COLOR = "#888888"
    HOVER_BG = "rgba(29, 185, 84, 0.08)"  # Light green tint on hover
    
    def __init__(self, index: int, segment: TranslationSegment, bilingual: bool = True, parent=None):
        super().__init__(parent)
        self.index = index
        self.segment = segment
        self.bilingual = bilingual
        self._is_current = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the subtitle item UI."""
        layout = QVBoxLayout(self)
        # Improved padding for clean typography (Requirements 4.5)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(4)
        
        # Time labels container
        time_text = f"{self.segment.format_start_time()} - {self.segment.format_end_time()}"
        self.time_label = QLabel(time_text)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(f"color: {self.TIME_COLOR}; font-size: 10px;")
        layout.addWidget(self.time_label)
        
        # Original text label with improved typography
        self.original_label = QLabel(self.segment.original_text)
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_label.setWordWrap(True)
        self.original_label.setFont(QFont("Microsoft YaHei", 14))
        layout.addWidget(self.original_label)
        
        # Translated text label (only if bilingual and different from original)
        self.translated_label = None
        if self.bilingual and self.segment.source_language != 'zh':
            self.translated_label = QLabel(self.segment.translated_text)
            self.translated_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.translated_label.setWordWrap(True)
            self.translated_label.setFont(QFont("Microsoft YaHei", 12))
            self.translated_label.setStyleSheet(f"color: {self.TEXT_SECONDARY};")
            layout.addWidget(self.translated_label)
        
        # Pointer cursor for clickable subtitles (Requirements 5.3)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        self._update_style()

    def set_current(self, is_current: bool):
        """Set whether this item is the currently playing subtitle."""
        if self._is_current != is_current:
            self._is_current = is_current
            self._update_style()
    
    def _update_style(self):
        """Update the visual style based on current state."""
        if self._is_current:
            # Current subtitle highlighted with primary color (Requirements 4.1)
            self.original_label.setStyleSheet(f"color: {self.PRIMARY_COLOR}; font-weight: bold;")
            if self.translated_label:
                self.translated_label.setStyleSheet(f"color: {self.PRIMARY_COLOR};")
            # Add subtle background highlight for current item
            self.setStyleSheet(f"""
                SubtitleItemWidget {{
                    background-color: {self.HOVER_BG};
                    border-radius: 8px;
                }}
            """)
        else:
            self.original_label.setStyleSheet(f"color: {self.TEXT_COLOR};")
            if self.translated_label:
                self.translated_label.setStyleSheet(f"color: {self.TEXT_SECONDARY};")
            self.setStyleSheet("")
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effect (Requirements 5.3)."""
        if not self._is_current:
            self.setStyleSheet(f"""
                SubtitleItemWidget {{
                    background-color: {self.HOVER_BG};
                    border-radius: 8px;
                }}
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave to remove hover effect."""
        if not self._is_current:
            self.setStyleSheet("")
        super().leaveEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse click to emit jump signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index, self.segment.start_time)
        super().mousePressEvent(event)


class SubtitleView(QWidget):
    """
    NetEase Cloud Music style scrolling subtitle view.
    
    Features:
    - Current sentence centered and highlighted
    - Smooth scrolling animation
    - Click-to-seek functionality
    - Bilingual or monolingual display mode
    """
    
    subtitle_clicked = pyqtSignal(int, float)  # index, start_time
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager: Optional[SubtitleManager] = None
        self._current_index: int = -1
        self._bilingual: bool = True
        self._subtitle_items: List[SubtitleItemWidget] = []
        self._scroll_animation: Optional[QPropertyAnimation] = None
        self._setup_ui()
    
    # Style constants for consistent theming (Requirements 4.1)
    PRIMARY_COLOR = "#1DB954"
    SCROLLBAR_BG = "#F0F0F0"
    SCROLLBAR_HANDLE = "#CCCCCC"
    SCROLLBAR_HANDLE_HOVER = "#1DB954"
    
    def _setup_ui(self):
        """Set up the main UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for subtitles with improved styling (Requirements 4.5)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: #FAFAFA;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {self.SCROLLBAR_BG};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.SCROLLBAR_HANDLE};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.PRIMARY_COLOR};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Container widget for subtitle items with adequate padding (Requirements 4.5)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        # Improved padding for clean typography
        self.container_layout.setContentsMargins(30, 100, 30, 100)
        self.container_layout.setSpacing(20)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Add spacer at top for centering effect
        self.container_layout.addStretch(1)
        
        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)
    
    def set_subtitles(self, manager: SubtitleManager):
        """
        Set the subtitle data from a SubtitleManager.
        
        Args:
            manager: SubtitleManager containing the subtitle segments
        """
        self._manager = manager
        self._current_index = -1
        self._rebuild_subtitle_items()

    def _rebuild_subtitle_items(self):
        """Rebuild all subtitle item widgets."""
        # Clear existing items
        for item in self._subtitle_items:
            item.deleteLater()
        self._subtitle_items.clear()
        
        # Remove all widgets from layout except the stretch
        while self.container_layout.count() > 0:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._manager or len(self._manager) == 0:
            self.container_layout.addStretch(1)
            return
        
        # Add top spacer for centering
        self.container_layout.addStretch(1)
        
        # Create subtitle items
        for i, segment in enumerate(self._manager.segments):
            item = SubtitleItemWidget(i, segment, self._bilingual, self.container)
            item.clicked.connect(self._on_subtitle_clicked)
            self._subtitle_items.append(item)
            self.container_layout.addWidget(item)
        
        # Add bottom spacer for centering
        self.container_layout.addStretch(1)
    
    def set_current_time(self, time: float):
        """
        Set the current playback time and update the display.
        
        This triggers scrolling to center the current subtitle.
        
        Args:
            time: Current playback time in seconds
        """
        if not self._manager:
            return
        
        new_index = self._manager.get_current_index(time)
        
        if new_index != self._current_index:
            # Update highlight
            if 0 <= self._current_index < len(self._subtitle_items):
                self._subtitle_items[self._current_index].set_current(False)
            
            self._current_index = new_index
            
            if 0 <= self._current_index < len(self._subtitle_items):
                self._subtitle_items[self._current_index].set_current(True)
                self._scroll_to_current()
    
    def _scroll_to_current(self):
        """Scroll to center the current subtitle with smooth animation."""
        if self._current_index < 0 or self._current_index >= len(self._subtitle_items):
            return
        
        current_item = self._subtitle_items[self._current_index]
        
        # Calculate target scroll position to center the item
        item_pos = current_item.pos().y()
        item_height = current_item.height()
        viewport_height = self.scroll_area.viewport().height()
        
        target_scroll = item_pos - (viewport_height // 2) + (item_height // 2)
        target_scroll = max(0, target_scroll)
        
        # Stop any existing animation
        if self._scroll_animation and self._scroll_animation.state() == QPropertyAnimation.State.Running:
            self._scroll_animation.stop()
        
        # Create smooth scroll animation
        scrollbar = self.scroll_area.verticalScrollBar()
        self._scroll_animation = QPropertyAnimation(scrollbar, b"value")
        self._scroll_animation.setDuration(300)
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(target_scroll)
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation.start()
    
    def set_display_mode(self, bilingual: bool):
        """
        Set the display mode.
        
        Args:
            bilingual: True for bilingual display (original + translation),
                      False for monolingual (original only)
        """
        if self._bilingual != bilingual:
            self._bilingual = bilingual
            self._rebuild_subtitle_items()
            
            # Restore current highlight
            if 0 <= self._current_index < len(self._subtitle_items):
                self._subtitle_items[self._current_index].set_current(True)
    
    def _on_subtitle_clicked(self, index: int, start_time: float):
        """
        Handle subtitle item click.
        
        Requirements 5.4: Immediately highlight the clicked subtitle as current.
        """
        # Update highlight immediately (Requirements 5.4)
        if 0 <= self._current_index < len(self._subtitle_items):
            self._subtitle_items[self._current_index].set_current(False)
        
        self._current_index = index
        
        if 0 <= index < len(self._subtitle_items):
            self._subtitle_items[index].set_current(True)
            self._scroll_to_current()
        
        # Emit signal for audio player seek
        self.subtitle_clicked.emit(index, start_time)
    
    def get_segment_start_time(self, index: int) -> Optional[float]:
        """
        Get the start time for a subtitle at the given index.
        
        Args:
            index: Index of the subtitle
            
        Returns:
            Start time in seconds, or None if index is invalid
        """
        if not self._manager:
            return None
        segment = self._manager.get_segment_by_index(index)
        return segment.start_time if segment else None
    
    @property
    def current_index(self) -> int:
        """Get the current subtitle index."""
        return self._current_index
    
    @property
    def bilingual(self) -> bool:
        """Get the current display mode."""
        return self._bilingual

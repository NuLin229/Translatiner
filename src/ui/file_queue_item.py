"""
FileQueueItem UI Widget - Single file item in the playback queue.

Implements a draggable file item with:
- File name display with icon
- Remove button (×)
- Visual states (current, processing, hover)
- Click and remove signals
- Drag-and-drop support for reordering

Requirements: 1.4, 2.1, 2.2, 2.3, 2.4, 4.2, 4.3, 6.3
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QMimeData, QPoint
from PyQt6.QtGui import QFont, QColor, QMovie, QDrag, QPixmap, QPainter

from src.models.data_models import FileState


class FileQueueItem(QFrame):
    """
    Single file item widget for the playback queue.
    
    Features:
    - Displays file name with icon
    - Remove button (×)
    - Visual states: current playing, processing, hover
    - Emits signals for click and remove actions
    
    Validates: Requirements 1.4, 4.2, 4.3, 6.3
    """
    
    # Signals
    clicked = pyqtSignal(int)           # Emitted when item is clicked, passes index
    remove_clicked = pyqtSignal(int)    # Emitted when remove button is clicked, passes index
    drag_started = pyqtSignal(int)      # Emitted when drag starts, passes index
    
    # MIME type for drag-and-drop
    MIME_TYPE = "application/x-filequeueitem"
    
    # Style constants
    PRIMARY_COLOR = "#1DB954"
    PRIMARY_HOVER = "#1ED760"
    BACKGROUND_DEFAULT = "#F8F9FA"
    BACKGROUND_CURRENT = "#E8F5E9"
    BACKGROUND_HOVER = "#F0FFF4"
    BORDER_DEFAULT = "#DDDDDD"
    TEXT_COLOR = "#333333"
    REMOVE_HOVER_COLOR = "#FF4444"
    
    def __init__(self, index: int, file_name: str, parent=None):
        """
        Initialize the FileQueueItem.
        
        Args:
            index: Index of this item in the queue.
            file_name: Name of the file to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._index = index
        self._file_name = file_name
        self._is_current = False
        self._state = FileState.PENDING
        self._drag_start_position = None
        self._is_drop_target = False
        
        self._setup_ui()
        self._apply_default_style()
        
        # Enable drag-and-drop
        self.setAcceptDrops(True)
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Set size constraints
        self.setFixedHeight(45)
        self.setMinimumWidth(120)
        self.setMaximumWidth(180)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(4)
        
        # File icon
        self._icon_label = QLabel("📁")
        self._icon_label.setFont(QFont("Segoe UI Emoji", 12))
        layout.addWidget(self._icon_label)
        
        # File name (truncated if too long)
        self._name_label = QLabel(self._file_name)
        self._name_label.setFont(QFont("Microsoft YaHei", 9))
        self._name_label.setStyleSheet(f"color: {self.TEXT_COLOR};")
        self._name_label.setMaximumWidth(100)
        self._name_label.setToolTip(self._file_name)
        layout.addWidget(self._name_label, 1)
        
        # Processing indicator (hidden by default)
        self._processing_label = QLabel("⏳")
        self._processing_label.setFont(QFont("Segoe UI Emoji", 10))
        self._processing_label.hide()
        layout.addWidget(self._processing_label)
        
        # Remove button
        self._remove_btn = QPushButton("×")
        self._remove_btn.setFixedSize(20, 20)
        self._remove_btn.setFont(QFont("Microsoft YaHei", 12))
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #888888;
                border: none;
            }}
            QPushButton:hover {{
                color: {self.REMOVE_HOVER_COLOR};
            }}
        """)
        self._remove_btn.clicked.connect(self._on_remove_clicked)
        layout.addWidget(self._remove_btn)
        
        # Add shadow effect
        self._add_shadow()
    
    def _add_shadow(self):
        """Add subtle shadow effect to the frame."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
    
    def _apply_default_style(self):
        """Apply the default (non-current) style with smooth transitions (Requirements 4.4)."""
        self.setStyleSheet(f"""
            FileQueueItem {{
                background-color: {self.BACKGROUND_DEFAULT};
                border: 1px solid {self.BORDER_DEFAULT};
                border-radius: 8px;
            }}
            FileQueueItem:hover {{
                border-color: {self.PRIMARY_COLOR};
                background-color: {self.BACKGROUND_HOVER};
            }}
        """)
    
    def _apply_current_style(self):
        """Apply the current playing style (green border) with smooth transitions (Requirements 4.4)."""
        self.setStyleSheet(f"""
            FileQueueItem {{
                background-color: {self.BACKGROUND_CURRENT};
                border: 2px solid {self.PRIMARY_COLOR};
                border-radius: 8px;
            }}
            FileQueueItem:hover {{
                background-color: #D4EDDA;
            }}
        """)
    
    def _apply_processing_style(self):
        """Apply the processing style with smooth transitions (Requirements 4.4)."""
        self.setStyleSheet(f"""
            FileQueueItem {{
                background-color: #FFF8E1;
                border: 2px solid #FFC107;
                border-radius: 8px;
            }}
            FileQueueItem:hover {{
                background-color: #FFECB3;
            }}
        """)
    
    def set_current(self, is_current: bool) -> None:
        """
        Set whether this item is the current playing item.
        
        Args:
            is_current: True if this is the current playing item.
            
        Requirements: 4.3
        """
        self._is_current = is_current
        self._update_visual_state()
    
    def set_state(self, state: FileState) -> None:
        """
        Set the file state.
        
        Args:
            state: New state for the file.
            
        Requirements: 6.3
        """
        self._state = state
        self._update_visual_state()
    
    def _update_visual_state(self):
        """Update the visual appearance based on current state."""
        # Show/hide processing indicator
        if self._state == FileState.PROCESSING:
            self._processing_label.show()
            self._icon_label.setText("⏳")
            self._apply_processing_style()
        else:
            self._processing_label.hide()
            self._icon_label.setText("📁")
            
            # Apply style based on current status
            if self._is_current:
                self._apply_current_style()
            else:
                self._apply_default_style()
    
    @property
    def index(self) -> int:
        """Get the index of this item."""
        return self._index
    
    @index.setter
    def index(self, value: int) -> None:
        """Set the index of this item."""
        self._index = value
    
    @property
    def file_name(self) -> str:
        """Get the file name."""
        return self._file_name
    
    @property
    def is_current(self) -> bool:
        """Check if this is the current playing item."""
        return self._is_current
    
    @property
    def state(self) -> FileState:
        """Get the current file state."""
        return self._state
    
    def _on_remove_clicked(self):
        """Handle remove button click."""
        self.remove_clicked.emit(self._index)
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release event - emit click if not dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_start_position is not None:
                # Only emit click if we didn't drag
                self.clicked.emit(self._index)
            self._drag_start_position = None
        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move event - start drag if threshold exceeded."""
        if self._drag_start_position is None:
            return
        
        # Check if we've moved far enough to start a drag
        if (event.pos() - self._drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        
        # Start drag operation
        self._start_drag(event)
        self._drag_start_position = None
    
    def _start_drag(self, event):
        """
        Start a drag operation.
        
        Requirements: 2.1, 2.3
        """
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store the index in the mime data
        mime_data.setData(self.MIME_TYPE, str(self._index).encode())
        drag.setMimeData(mime_data)
        
        # Create a pixmap of this widget for the drag preview
        pixmap = self.grab()
        
        # Make the pixmap semi-transparent
        transparent_pixmap = QPixmap(pixmap.size())
        transparent_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(transparent_pixmap)
        painter.setOpacity(0.7)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        drag.setPixmap(transparent_pixmap)
        drag.setHotSpot(event.pos())
        
        # Emit signal that drag started
        self.drag_started.emit(self._index)
        
        # Execute the drag
        drag.exec(Qt.DropAction.MoveAction)
    
    def enterEvent(self, event):
        """Handle mouse enter event for hover effect."""
        if not self._is_current and self._state != FileState.PROCESSING:
            # Enhance shadow on hover
            shadow = self.graphicsEffect()
            if isinstance(shadow, QGraphicsDropShadowEffect):
                shadow.setBlurRadius(12)
                shadow.setColor(QColor(0, 0, 0, 50))
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        if not self._is_current and self._state != FileState.PROCESSING:
            # Reset shadow
            shadow = self.graphicsEffect()
            if isinstance(shadow, QGraphicsDropShadowEffect):
                shadow.setBlurRadius(8)
                shadow.setColor(QColor(0, 0, 0, 30))
        super().leaveEvent(event)
    
    def set_drop_target(self, is_target: bool, position: str = "left") -> None:
        """
        Set whether this item is a drop target.
        
        Args:
            is_target: True if this is a drop target.
            position: "left" or "right" to indicate drop position.
            
        Requirements: 2.4
        """
        self._is_drop_target = is_target
        self._drop_position = position if is_target else None
        self._update_drop_target_style()
    
    def _update_drop_target_style(self):
        """Update the visual style for drop target indication."""
        if self._is_drop_target:
            # Show a colored border on the drop side
            if self._drop_position == "left":
                self.setStyleSheet(f"""
                    FileQueueItem {{
                        background-color: {self.BACKGROUND_HOVER};
                        border: 1px solid {self.BORDER_DEFAULT};
                        border-left: 3px solid {self.PRIMARY_COLOR};
                        border-radius: 8px;
                    }}
                """)
            else:
                self.setStyleSheet(f"""
                    FileQueueItem {{
                        background-color: {self.BACKGROUND_HOVER};
                        border: 1px solid {self.BORDER_DEFAULT};
                        border-right: 3px solid {self.PRIMARY_COLOR};
                        border-radius: 8px;
                    }}
                """)
        else:
            # Restore normal style
            self._update_visual_state()
    
    @property
    def is_drop_target(self) -> bool:
        """Check if this item is currently a drop target."""
        return self._is_drop_target

"""
FileQueue UI Widget - Multi-file playback queue component.

Implements file queue functionality with:
- Support for up to 5 audio files
- Drag-and-drop reordering
- Visual state indicators
- File selection and removal

Requirements: 1.1, 1.2, 1.3, 1.5, 2.1, 2.2, 2.3, 2.4, 6.1, 6.2
"""

import os
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFileDialog, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDragMoveEvent, QDropEvent

from src.models.file_queue import FileQueue as FileQueueLogic
from src.models.data_models import FileState, PlaylistItem
from src.ui.file_queue_item import FileQueueItem


class FileQueueWidget(QWidget):
    """
    Multi-file playback queue UI widget.
    
    Features:
    - Add up to 5 audio files (wav/mp3)
    - Display files in horizontal layout
    - Remove files from queue
    - Drag-and-drop reordering
    - Visual state indicators
    
    Validates: Requirements 1.1, 1.3
    """
    
    # Signals
    file_selected = pyqtSignal(str)      # Emitted when a file is selected for processing
    queue_changed = pyqtSignal(list)     # Emitted when queue contents change
    
    # Constants
    MAX_FILES = 5
    SUPPORTED_FORMATS = "音频文件 (*.wav *.mp3);;WAV 文件 (*.wav);;MP3 文件 (*.mp3)"
    
    def __init__(self, parent=None):
        """Initialize the FileQueue widget."""
        super().__init__(parent)
        self._queue = FileQueueLogic()
        self._dragging_index = -1  # Index of item being dragged
        self._drop_target_index = -1  # Index of current drop target
        self._drop_position = "left"  # "left" or "right" of target
        self._setup_ui()
        
        # Enable drop events on this widget
        self.setAcceptDrops(True)
    
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(8)
        
        # Empty state button - shown when queue is empty
        # Requirements: 3.3
        self._empty_state_button = QPushButton("📁 添加文件")
        self._empty_state_button.setFixedHeight(40)
        self._empty_state_button.setFont(QFont("Microsoft YaHei", 11))
        self._empty_state_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        self._empty_state_button.clicked.connect(self._on_add_clicked)
        main_layout.addWidget(self._empty_state_button)
        
        # Container for file items
        self._items_container = QWidget()
        self._items_layout = QHBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(8)
        
        main_layout.addWidget(self._items_container)
        main_layout.addStretch(1)
        
        # Add button ("+") - shown when queue has files but not full
        # Requirements: 3.4
        self._add_button = QPushButton("+")
        self._add_button.setFixedSize(40, 40)
        self._add_button.setFont(QFont("Microsoft YaHei", 16))
        self._add_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self._add_button.clicked.connect(self._on_add_clicked)
        main_layout.addWidget(self._add_button)
        
        # Set fixed height for the widget
        # Requirements: 3.2
        self.setFixedHeight(60)
        
        # Update UI to show empty state
        self._update_ui()
    
    def _on_add_clicked(self):
        """Handle add button click."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            self.SUPPORTED_FORMATS
        )
        
        if file_paths:
            self.add_files(file_paths)
    
    def add_files(self, file_paths: List[str]) -> int:
        """
        Add files to the queue.
        
        Args:
            file_paths: List of file paths to add.
            
        Returns:
            Number of files actually added.
            
        Requirements: 1.1, 1.2
        """
        # Count how many files we can add
        available_slots = self.MAX_FILES - self._queue.count
        valid_paths = [p for p in file_paths if self._is_valid_format(p)]
        
        # Show warning if some files will be rejected
        rejected_count = len(file_paths) - len(valid_paths)
        if rejected_count > 0:
            QMessageBox.warning(
                self,
                "格式不支持",
                f"{rejected_count} 个文件格式不支持，仅支持 wav/mp3 格式。"
            )
        
        # Check if we'll exceed the limit
        if len(valid_paths) > available_slots:
            QMessageBox.warning(
                self,
                "文件数量超限",
                f"最多支持 {self.MAX_FILES} 个文件。已添加 {available_slots} 个文件。"
            )
        
        # Add files using the queue logic
        added = self._queue.add_files(file_paths)
        
        if added > 0:
            self._update_ui()
            self.queue_changed.emit(self._get_file_paths())
            
            # If this is the first file, emit file_selected
            if self._queue.count == added:
                self._queue.set_current_index(0)
                self.file_selected.emit(self._queue.current_file)
        
        return added
    
    def _is_valid_format(self, file_path: str) -> bool:
        """Check if file has a supported format."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in {'.wav', '.mp3'}
    
    def remove_file(self, index: int) -> bool:
        """
        Remove a file at the specified index.
        
        Args:
            index: Index of the file to remove.
            
        Returns:
            True if removal was successful.
            
        Requirements: 1.5
        """
        result = self._queue.remove_file(index)
        if result:
            self._update_ui()
            self.queue_changed.emit(self._get_file_paths())
        return result
    
    def move_file(self, from_index: int, to_index: int) -> bool:
        """
        Move a file from one position to another.
        
        Args:
            from_index: Current index of the file.
            to_index: Target index for the file.
            
        Returns:
            True if move was successful.
            
        Requirements: 2.1, 2.2
        """
        result = self._queue.move_file(from_index, to_index)
        if result:
            self._update_ui()
            self.queue_changed.emit(self._get_file_paths())
        return result
    
    def get_next_file(self) -> Optional[str]:
        """
        Get the next file to play.
        
        Returns:
            Path of the next file, or None if no more files.
            
        Requirements: 6.1, 6.2
        """
        next_file = self._queue.get_next_file()
        if next_file:
            self._update_ui()
        return next_file
    
    def set_current_index(self, index: int) -> bool:
        """
        Set the current playing file index.
        
        Args:
            index: Index to set as current.
            
        Returns:
            True if successful.
            
        Requirements: 6.1, 6.2
        """
        result = self._queue.set_current_index(index)
        if result:
            self._update_ui()
        return result
    
    def set_file_state(self, index: int, state: FileState) -> bool:
        """
        Set the state of a file at the specified index.
        
        Args:
            index: Index of the file.
            state: New state for the file.
            
        Returns:
            True if successful.
        """
        result = self._queue.set_file_state(index, state)
        if result:
            self._update_ui()
        return result
    
    @property
    def current_file(self) -> Optional[str]:
        """Get the current playing file path."""
        return self._queue.current_file
    
    @property
    def current_index(self) -> int:
        """Get the current playing file index."""
        return self._queue.current_index
    
    @property
    def is_full(self) -> bool:
        """Check if the queue is at maximum capacity."""
        return self._queue.is_full
    
    @property
    def has_next(self) -> bool:
        """Check if there is a next file in the queue."""
        return self._queue.has_next
    
    @property
    def count(self) -> int:
        """Get the number of files in the queue."""
        return self._queue.count
    
    @property
    def items(self) -> List[PlaylistItem]:
        """Get all items in the queue."""
        return self._queue.items
    
    @property
    def is_add_button_enabled(self) -> bool:
        """Check if the add button is enabled.
        
        The add button should be enabled when queue has files but is not full.
        Requirements: 3.4
        """
        # When empty, the empty state button is shown instead
        if self._queue.count == 0:
            return True  # Empty state button is always enabled
        return self._add_button.isEnabled()
    
    def _get_file_paths(self) -> List[str]:
        """Get list of all file paths in the queue."""
        return [item.file_path for item in self._queue.items]
    
    def _update_ui(self):
        """Update the UI to reflect current queue state.
        
        Requirements: 3.3, 3.4
        """
        # Clear existing items
        while self._items_layout.count():
            child = self._items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Handle empty state vs non-empty state
        is_empty = self._queue.count == 0
        
        # Show/hide empty state button
        self._empty_state_button.setVisible(is_empty)
        
        # Show/hide items container and add button based on empty state
        self._items_container.setVisible(not is_empty)
        self._add_button.setVisible(not is_empty)
        
        if not is_empty:
            # Add items for each file in queue
            for i, item in enumerate(self._queue.items):
                item_widget = self._create_item_widget(i, item)
                self._items_layout.addWidget(item_widget)
            
            # Update add button state - enabled only if queue is not full
            # Requirements: 3.4
            self._add_button.setEnabled(not self._queue.is_full)
    
    def _create_item_widget(self, index: int, item: PlaylistItem) -> FileQueueItem:
        """
        Create a FileQueueItem widget for a single file item.
        
        Args:
            index: Index of the item in the queue.
            item: PlaylistItem data.
            
        Returns:
            FileQueueItem widget configured for this item.
            
        Requirements: 1.4
        """
        # Create the FileQueueItem widget
        item_widget = FileQueueItem(index, item.file_name, self)
        
        # Set current state
        is_current = index == self._queue.current_index
        item_widget.set_current(is_current)
        
        # Set file state
        item_widget.set_state(item.state)
        
        # Connect signals
        item_widget.clicked.connect(self._on_item_clicked)
        item_widget.remove_clicked.connect(self._on_remove_clicked)
        item_widget.drag_started.connect(self._on_drag_started)
        
        return item_widget
    
    def _on_remove_clicked(self, index: int):
        """Handle remove button click."""
        self.remove_file(index)
    
    def _on_item_clicked(self, index: int):
        """Handle file item click - switch to that file."""
        if index != self._queue.current_index:
            if self.set_current_index(index):
                self.file_selected.emit(self._queue.current_file)
    
    def _on_drag_started(self, index: int):
        """Handle drag start from a FileQueueItem."""
        self._dragging_index = index
    
    # ==================== Drag-and-Drop Event Handlers ====================
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        Handle drag enter event.
        
        Requirements: 2.1, 2.3
        """
        if event.mimeData().hasFormat(FileQueueItem.MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """
        Handle drag move event - update drop target visual feedback.
        
        Requirements: 2.3, 2.4
        """
        if not event.mimeData().hasFormat(FileQueueItem.MIME_TYPE):
            event.ignore()
            return
        
        event.acceptProposedAction()
        
        # Find which item we're over
        pos = event.position().toPoint()
        target_index, position = self._find_drop_target(pos)
        
        # Update visual feedback if target changed
        if target_index != self._drop_target_index or position != self._drop_position:
            self._clear_drop_target_highlight()
            self._drop_target_index = target_index
            self._drop_position = position
            self._set_drop_target_highlight()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event - clear visual feedback."""
        self._clear_drop_target_highlight()
        self._drop_target_index = -1
        self._dragging_index = -1
    
    def dropEvent(self, event: QDropEvent):
        """
        Handle drop event - reorder the queue.
        
        Requirements: 2.1, 2.2
        """
        if not event.mimeData().hasFormat(FileQueueItem.MIME_TYPE):
            event.ignore()
            return
        
        # Get the source index from mime data
        source_index = int(event.mimeData().data(FileQueueItem.MIME_TYPE).data().decode())
        
        # Calculate the target index
        target_index = self._calculate_drop_index(source_index)
        
        # Clear visual feedback
        self._clear_drop_target_highlight()
        
        # Perform the move if indices are different
        if target_index != source_index and target_index != -1:
            self.move_file(source_index, target_index)
        
        # Reset drag state
        self._dragging_index = -1
        self._drop_target_index = -1
        
        event.acceptProposedAction()
    
    def _find_drop_target(self, pos) -> tuple:
        """
        Find the drop target item and position based on mouse position.
        
        Args:
            pos: Mouse position in widget coordinates.
            
        Returns:
            Tuple of (target_index, position) where position is "left" or "right".
        """
        # Iterate through item widgets to find which one we're over
        for i in range(self._items_layout.count()):
            item = self._items_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget_rect = widget.geometry()
                
                # Check if position is within this widget's horizontal bounds
                if widget_rect.left() <= pos.x() <= widget_rect.right():
                    # Determine if we're on the left or right half
                    mid_x = widget_rect.center().x()
                    if pos.x() < mid_x:
                        return (i, "left")
                    else:
                        return (i, "right")
        
        # If we're past all items, target the last position
        if self._items_layout.count() > 0:
            return (self._items_layout.count() - 1, "right")
        
        return (-1, "left")
    
    def _calculate_drop_index(self, source_index: int) -> int:
        """
        Calculate the actual drop index based on current drop target.
        
        Args:
            source_index: Index of the item being dragged.
            
        Returns:
            Target index for the move operation.
        """
        if self._drop_target_index == -1:
            return -1
        
        target = self._drop_target_index
        
        # Adjust for position (left = before, right = after)
        if self._drop_position == "right":
            target += 1
        
        # Adjust if moving from before the target
        if source_index < target:
            target -= 1
        
        return target
    
    def _set_drop_target_highlight(self):
        """Set visual highlight on the current drop target."""
        if self._drop_target_index >= 0 and self._drop_target_index < self._items_layout.count():
            item = self._items_layout.itemAt(self._drop_target_index)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, FileQueueItem):
                    widget.set_drop_target(True, self._drop_position)
    
    def _clear_drop_target_highlight(self):
        """Clear visual highlight from all items."""
        for i in range(self._items_layout.count()):
            item = self._items_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, FileQueueItem):
                    widget.set_drop_target(False)
    
    def clear(self):
        """Clear all files from the queue."""
        self._queue.clear()
        self._update_ui()
        self.queue_changed.emit([])

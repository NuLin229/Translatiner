"""FileQueue core logic for managing the playback queue."""

from typing import List, Optional
from .data_models import FileState, PlaylistItem
import os


class FileQueue:
    """Core logic for managing a queue of audio files.
    
    This class handles the data management for the file queue,
    separate from UI concerns.
    """
    
    MAX_FILES = 5
    SUPPORTED_FORMATS = {'.wav', '.mp3'}
    
    def __init__(self):
        self._items: List[PlaylistItem] = []
        self._current_index: int = -1
    
    @property
    def items(self) -> List[PlaylistItem]:
        """Get all items in the queue."""
        return self._items.copy()
    
    @property
    def count(self) -> int:
        """Get the number of files in the queue."""
        return len(self._items)
    
    @property
    def is_full(self) -> bool:
        """Check if the queue is at maximum capacity."""
        return len(self._items) >= self.MAX_FILES
    
    @property
    def current_index(self) -> int:
        """Get the current playing file index."""
        return self._current_index
    
    @property
    def current_file(self) -> Optional[str]:
        """Get the current playing file path."""
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index].file_path
        return None
    
    @property
    def has_next(self) -> bool:
        """Check if there is a next file in the queue."""
        return self._current_index < len(self._items) - 1
    
    def _is_valid_format(self, file_path: str) -> bool:
        """Check if the file has a supported format."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.SUPPORTED_FORMATS
    
    def add_files(self, file_paths: List[str]) -> int:
        """Add files to the queue.
        
        Args:
            file_paths: List of file paths to add.
            
        Returns:
            Number of files actually added.
        """
        added = 0
        for path in file_paths:
            if self.is_full:
                break
            if not self._is_valid_format(path):
                continue
            
            file_name = os.path.basename(path)
            item = PlaylistItem(file_path=path, file_name=file_name)
            self._items.append(item)
            added += 1
        
        return added
    
    def remove_file(self, index: int) -> bool:
        """Remove a file at the specified index.
        
        Args:
            index: Index of the file to remove.
            
        Returns:
            True if removal was successful, False otherwise.
        """
        if not (0 <= index < len(self._items)):
            return False
        
        self._items.pop(index)
        
        # Adjust current index if needed
        if self._current_index >= len(self._items):
            self._current_index = len(self._items) - 1
        elif index < self._current_index:
            self._current_index -= 1
        
        return True
    
    def move_file(self, from_index: int, to_index: int) -> bool:
        """Move a file from one position to another.
        
        Args:
            from_index: Current index of the file.
            to_index: Target index for the file.
            
        Returns:
            True if move was successful, False otherwise.
        """
        if not (0 <= from_index < len(self._items)):
            return False
        if not (0 <= to_index < len(self._items)):
            return False
        if from_index == to_index:
            return True
        
        item = self._items.pop(from_index)
        self._items.insert(to_index, item)
        
        # Adjust current index if needed
        if self._current_index == from_index:
            self._current_index = to_index
        elif from_index < self._current_index <= to_index:
            self._current_index -= 1
        elif to_index <= self._current_index < from_index:
            self._current_index += 1
        
        return True
    
    def get_next_file(self) -> Optional[str]:
        """Get the next file to play.
        
        Returns:
            Path of the next file, or None if no more files.
        """
        if self.has_next:
            self._current_index += 1
            return self._items[self._current_index].file_path
        return None
    
    def set_current_index(self, index: int) -> bool:
        """Set the current playing file index.
        
        Args:
            index: Index to set as current.
            
        Returns:
            True if successful, False otherwise.
        """
        if not (0 <= index < len(self._items)):
            return False
        self._current_index = index
        return True
    
    def set_file_state(self, index: int, state: FileState) -> bool:
        """Set the state of a file at the specified index.
        
        When setting PROCESSING state, ensures no other file has PROCESSING state.
        
        Args:
            index: Index of the file.
            state: New state for the file.
            
        Returns:
            True if successful, False otherwise.
            
        Requirements 6.3: Only one file can have PROCESSING state at a time.
        """
        if not (0 <= index < len(self._items)):
            return False
        
        # If setting to PROCESSING, clear PROCESSING from all other files
        if state == FileState.PROCESSING:
            for i, item in enumerate(self._items):
                if i != index and item.state == FileState.PROCESSING:
                    item.state = FileState.PENDING
        
        self._items[index].state = state
        return True
    
    def clear(self) -> None:
        """Clear all files from the queue."""
        self._items.clear()
        self._current_index = -1

"""Subtitle manager for synchronizing subtitles with audio playback."""

import json
from typing import List, Optional

from src.models.data_models import TranslationSegment, TranslationResult


class SubtitleManager:
    """Manages subtitle data and synchronization with audio playback."""
    
    def __init__(self, segments: List[TranslationSegment] = None):
        """
        Initialize subtitle manager.
        
        Args:
            segments: List of translation segments to manage
        """
        self._segments: List[TranslationSegment] = segments or []
    
    @property
    def segments(self) -> List[TranslationSegment]:
        """Get the list of segments."""
        return self._segments
    
    def get_current_index(self, current_time: float) -> int:
        """
        Get the index of the subtitle segment for the given playback time.
        
        For any playback time t, returns index i where:
        segments[i].start_time <= t < segments[i].end_time
        
        Args:
            current_time: Current playback time in seconds
            
        Returns:
            Index of the current segment, or -1 if no segment matches
        """
        if not self._segments:
            return -1
        
        for i, segment in enumerate(self._segments):
            if segment.start_time <= current_time < segment.end_time:
                return i
        
        # If time is before first segment
        if current_time < self._segments[0].start_time:
            return -1
        
        # If time is after last segment
        if current_time >= self._segments[-1].end_time:
            return -1
        
        return -1
    
    def get_segment_by_index(self, index: int) -> Optional[TranslationSegment]:
        """
        Get the subtitle segment at the specified index.
        
        Args:
            index: Index of the segment to retrieve
            
        Returns:
            TranslationSegment at the index, or None if index is out of bounds
        """
        if index < 0 or index >= len(self._segments):
            return None
        return self._segments[index]
    
    def to_json(self) -> str:
        """
        Serialize the subtitle manager to JSON.
        
        Returns:
            JSON string representation
        """
        data = {
            'segments': [
                {
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'original_text': seg.original_text,
                    'translated_text': seg.translated_text,
                    'source_language': seg.source_language,
                    'target_language': seg.target_language
                }
                for seg in self._segments
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SubtitleManager':
        """
        Deserialize a SubtitleManager from JSON.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            SubtitleManager instance
        """
        data = json.loads(json_str)
        segments = [
            TranslationSegment(
                start_time=seg['start_time'],
                end_time=seg['end_time'],
                original_text=seg['original_text'],
                translated_text=seg['translated_text'],
                source_language=seg['source_language'],
                target_language=seg['target_language']
            )
            for seg in data['segments']
        ]
        return cls(segments)
    
    def __len__(self) -> int:
        """Return the number of segments."""
        return len(self._segments)

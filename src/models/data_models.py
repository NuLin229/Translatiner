"""Data models for the audio translator application."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, TYPE_CHECKING
from enum import Enum
import json
from datetime import datetime

if TYPE_CHECKING:
    from ..services.subtitle_manager import SubtitleManager


class FileState(Enum):
    """State of a file in the playback queue."""
    PENDING = "pending"       # Waiting to be processed
    PROCESSING = "processing" # Currently being processed
    READY = "ready"          # Processed and ready to play
    PLAYING = "playing"      # Currently playing
    COMPLETED = "completed"  # Playback completed


@dataclass
class PlaylistItem:
    """Represents a file in the playback queue."""
    file_path: str
    file_name: str
    state: FileState = FileState.PENDING
    subtitle_manager: Optional['SubtitleManager'] = None


@dataclass
class TranscriptSegment:
    """Represents a transcribed segment from speech recognition."""
    start_time: float  # Start time in seconds
    end_time: float    # End time in seconds
    text: str          # Recognized text
    language: str      # Source language code


@dataclass
class TranslationSegment:
    """Represents a translated segment with timing information."""
    start_time: float       # Start time in seconds
    end_time: float         # End time in seconds
    original_text: str      # Original text
    translated_text: str    # Translated text (same as original if Chinese)
    source_language: str    # Source language code
    target_language: str    # Target language code
    
    def format_start_time(self) -> str:
        """Format start time as HH:MM:SS."""
        return self._format_time(self.start_time)
    
    def format_end_time(self) -> str:
        """Format end time as HH:MM:SS."""
        return self._format_time(self.end_time)
    
    def _format_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class LanguageConfig:
    """Configuration for source and target languages."""
    source_language: str  # Source language code: ja, en, ko, zh
    target_language: str  # Target language code
    
    SUPPORTED_LANGUAGES = {
        'ja': '日语',
        'en': '英语',
        'ko': '韩语',
        'zh': '中文'
    }
    
    def is_valid_language(self, lang_code: str) -> bool:
        """Check if a language code is supported."""
        return lang_code in self.SUPPORTED_LANGUAGES


@dataclass
class TranslationResult:
    """Complete translation result with all segments."""
    audio_file: str                         # Audio file path
    source_language: str                    # Source language
    target_language: str                    # Target language
    segments: List[TranslationSegment]      # Translation segments
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'audio_file': self.audio_file,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'segments': [
                {
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'original_text': seg.original_text,
                    'translated_text': seg.translated_text,
                    'source_language': seg.source_language,
                    'target_language': seg.target_language
                }
                for seg in self.segments
            ],
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TranslationResult':
        """Create from dictionary."""
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
        return cls(
            audio_file=data['audio_file'],
            source_language=data['source_language'],
            target_language=data['target_language'],
            segments=segments,
            created_at=data['created_at']
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TranslationResult':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

"""Audio processor module for loading and processing audio files."""

import os
import wave
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class AudioData:
    """Container for loaded audio data."""
    file_path: str
    duration: float  # Duration in seconds
    sample_rate: int
    channels: int
    raw_data: Any = None  # Raw audio data for processing


class AudioProcessorError(Exception):
    """Exception raised for audio processing errors."""
    pass


class AudioProcessor:
    """Handles loading and processing of audio files.
    
    Supports wav and mp3 formats as specified in requirements 1.2, 1.3, 1.4.
    """
    
    SUPPORTED_EXTENSIONS = {'.wav', '.mp3'}
    
    def __init__(self):
        self._audio_data: Optional[AudioData] = None
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if the file format is supported.
        
        Args:
            file_path: Path to the audio file.
            
        Returns:
            True if the file extension is .wav or .mp3, False otherwise.
            
        Validates: Requirements 1.4
        """
        if not file_path:
            return False
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.SUPPORTED_EXTENSIONS
    
    def load_file(self, file_path: str) -> AudioData:
        """Load an audio file.
        
        Args:
            file_path: Path to the audio file (wav or mp3).
            
        Returns:
            AudioData containing the loaded audio information.
            
        Raises:
            AudioProcessorError: If the file doesn't exist, format is unsupported,
                                or the file cannot be read.
                                
        Validates: Requirements 1.2, 1.3
        """
        # Normalize the file path for Windows compatibility
        file_path = os.path.normpath(file_path)
        
        # Check if file exists
        if not os.path.isfile(file_path):
            raise AudioProcessorError(f"文件不存在: {file_path}")
        
        # Check format
        if not self.is_supported_format(file_path):
            raise AudioProcessorError("仅支持 wav 和 mp3 格式")
        
        try:
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            if ext == '.wav':
                self._audio_data = self._load_wav(file_path)
            elif ext == '.mp3':
                self._audio_data = self._load_mp3(file_path)
            else:
                raise AudioProcessorError("仅支持 wav 和 mp3 格式")
            
            return self._audio_data
            
        except Exception as e:
            if isinstance(e, AudioProcessorError):
                raise
            raise AudioProcessorError(f"文件无法读取: {str(e)}")
    
    def _load_wav(self, file_path: str) -> AudioData:
        """Load a WAV file using the standard library."""
        with wave.open(file_path, 'rb') as wav_file:
            n_channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            duration = n_frames / sample_rate
            raw_data = wav_file.readframes(n_frames)
            
            return AudioData(
                file_path=file_path,
                duration=duration,
                sample_rate=sample_rate,
                channels=n_channels,
                raw_data=raw_data
            )
    
    def _load_mp3(self, file_path: str) -> AudioData:
        """Load an MP3 file.
        
        Note: MP3 loading requires additional libraries. For now, we use
        a basic approach that works with Whisper which handles MP3 directly.
        """
        # For MP3 files, we'll store the file path and let Whisper handle it
        # Whisper can load MP3 files directly
        # We estimate duration by file size (rough estimate)
        file_size = os.path.getsize(file_path)
        # Rough estimate: 128kbps = 16KB/s
        estimated_duration = file_size / 16000
        
        return AudioData(
            file_path=file_path,
            duration=estimated_duration,  # Estimated, Whisper will get actual
            sample_rate=44100,  # Common MP3 sample rate
            channels=2,  # Assume stereo
            raw_data=None  # Whisper will load directly
        )
    
    def get_duration(self) -> float:
        """Get the duration of the loaded audio file.
        
        Returns:
            Duration in seconds.
            
        Raises:
            AudioProcessorError: If no audio file has been loaded.
        """
        if self._audio_data is None:
            raise AudioProcessorError("没有加载音频文件")
        return self._audio_data.duration

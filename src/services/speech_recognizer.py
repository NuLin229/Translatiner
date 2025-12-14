"""Speech recognizer module using OpenAI Whisper for transcription."""

from typing import List, Callable, Optional
import os
import tempfile
import subprocess

from src.models.data_models import TranscriptSegment
from src.services.audio_processor import AudioData


class SpeechRecognizerError(Exception):
    """Exception raised for speech recognition errors."""
    pass


def _convert_to_wav(input_path: str) -> str:
    """Convert audio file to WAV format using FFmpeg.
    
    This avoids memory issues with Whisper's internal FFmpeg calls on Python 3.14.
    
    Args:
        input_path: Path to the input audio file.
        
    Returns:
        Path to the temporary WAV file.
    """
    # Create a temporary WAV file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
    os.close(temp_fd)
    
    try:
        # Use FFmpeg to convert to WAV (16kHz mono, which Whisper prefers)
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',      # Mono
            '-c:a', 'pcm_s16le',  # 16-bit PCM
            temp_path
        ]
        
        # Run FFmpeg with proper output handling to avoid memory issues
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Read output in chunks to avoid memory buildup
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            os.unlink(temp_path)
            raise SpeechRecognizerError(f"FFmpeg 转换失败: {stderr.decode('utf-8', errors='ignore')}")
        
        return temp_path
        
    except FileNotFoundError:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise SpeechRecognizerError("FFmpeg 未找到，请确保 FFmpeg 已安装并在 PATH 中")


class SpeechRecognizer:
    """Speech recognizer using OpenAI Whisper model.
    
    Supports recognition of Japanese (ja), English (en), Korean (ko), 
    and Chinese (zh) audio content.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8
    """
    
    SUPPORTED_LANGUAGES = {'ja', 'en', 'ko', 'zh'}
    
    # Whisper language codes mapping
    LANGUAGE_MAP = {
        'ja': 'japanese',
        'en': 'english',
        'ko': 'korean',
        'zh': 'chinese'
    }
    
    def __init__(self, model_size: str = "base"):
        """Initialize the speech recognizer.
        
        Args:
            model_size: Whisper model size. Options: tiny, base, small, medium, large.
                       Default is 'base' for balance of speed and accuracy.
        """
        self._model_size = model_size
        self._model = None
        self._progress_callback: Optional[Callable[[float], None]] = None
    
    def _load_model(self):
        """Load the Whisper model lazily.
        
        Raises:
            SpeechRecognizerError: If model loading fails.
        """
        if self._model is not None:
            return
        
        try:
            import whisper
            self._model = whisper.load_model(self._model_size)
        except ImportError:
            raise SpeechRecognizerError(
                "语音识别模型加载失败: whisper 库未安装。请运行 'pip install openai-whisper'"
            )
        except Exception as e:
            raise SpeechRecognizerError(f"语音识别模型加载失败: {str(e)}")
    
    def set_progress_callback(self, callback: Callable[[float], None]) -> None:
        """Set a callback function for progress updates.
        
        Args:
            callback: Function that receives progress as a float (0.0 to 1.0).
            
        Validates: Requirements 3.8
        """
        self._progress_callback = callback
    
    def _report_progress(self, progress: float) -> None:
        """Report progress to the callback if set."""
        if self._progress_callback is not None:
            self._progress_callback(min(1.0, max(0.0, progress)))

    def recognize(self, audio_data: AudioData, language: str) -> List[TranscriptSegment]:
        """Recognize speech in the audio and return transcribed segments.
        
        Args:
            audio_data: AudioData object containing the audio file information.
            language: Source language code (ja, en, ko, zh).
            
        Returns:
            List of TranscriptSegment objects with timing and text information.
            
        Raises:
            SpeechRecognizerError: If recognition fails or language is not supported.
            
        Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
        """
        # Validate language
        if language not in self.SUPPORTED_LANGUAGES:
            raise SpeechRecognizerError(
                f"不支持的语言: {language}。支持的语言: {', '.join(self.SUPPORTED_LANGUAGES)}"
            )
        
        # Check file exists (normalize path for Windows compatibility)
        file_path = os.path.normpath(audio_data.file_path)
        if not os.path.isfile(file_path):
            raise SpeechRecognizerError(f"音频文件不存在: {file_path}")
        
        # Load model
        self._report_progress(0.1)
        self._load_model()
        self._report_progress(0.2)
        
        temp_wav_path = None
        try:
            # Get Whisper language name
            whisper_language = self.LANGUAGE_MAP.get(language, language)
            
            # Convert to WAV first to avoid memory issues with Whisper's FFmpeg calls
            self._report_progress(0.25)
            _, ext = os.path.splitext(file_path)
            if ext.lower() != '.wav':
                temp_wav_path = _convert_to_wav(file_path)
                transcribe_path = temp_wav_path
            else:
                transcribe_path = file_path
            
            # Perform transcription
            self._report_progress(0.3)
            result = self._model.transcribe(
                transcribe_path,
                language=whisper_language,
                task="transcribe",
                verbose=False
            )
            self._report_progress(0.9)
            
            # Convert Whisper segments to TranscriptSegment objects
            segments = self._convert_segments(result, language)
            
            self._report_progress(1.0)
            return segments
            
        except Exception as e:
            if isinstance(e, SpeechRecognizerError):
                raise
            raise SpeechRecognizerError(f"语音识别失败: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
    
    def _convert_segments(self, whisper_result: dict, language: str) -> List[TranscriptSegment]:
        """Convert Whisper result to TranscriptSegment list.
        
        Args:
            whisper_result: Result dictionary from Whisper transcription.
            language: Source language code.
            
        Returns:
            List of TranscriptSegment objects.
        """
        segments = []
        
        if 'segments' not in whisper_result:
            # If no segments, create one from the full text
            if whisper_result.get('text', '').strip():
                segments.append(TranscriptSegment(
                    start_time=0.0,
                    end_time=0.0,
                    text=whisper_result['text'].strip(),
                    language=language
                ))
            return segments
        
        for seg in whisper_result['segments']:
            text = seg.get('text', '').strip()
            if not text:
                continue
                
            segments.append(TranscriptSegment(
                start_time=float(seg.get('start', 0.0)),
                end_time=float(seg.get('end', 0.0)),
                text=text,
                language=language
            ))
        
        return segments
    
    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported for recognition.
        
        Args:
            language: Language code to check.
            
        Returns:
            True if the language is supported, False otherwise.
        """
        return language in self.SUPPORTED_LANGUAGES

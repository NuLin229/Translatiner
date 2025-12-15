"""
MainWindow - Main application window for audio translator.
"""

from typing import Optional, Dict
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QMessageBox, QApplication, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.ui.language_selector import LanguageSelector
from src.ui.subtitle_view import SubtitleView
from src.ui.audio_player import AudioPlayer
from src.ui.file_queue import FileQueueWidget
from src.ui.export_dialog import ExportDialog
from src.models.data_models import FileState
from src.services.audio_processor import AudioProcessor, AudioProcessorError
from src.services.speech_recognizer import SpeechRecognizer, SpeechRecognizerError
from src.services.translator import Translator, TranslatorError
from src.services.subtitle_manager import SubtitleManager


# =========================
# 后台处理线程
# =========================
class ProcessingWorker(QThread):
    progress_updated = pyqtSignal(float, str)
    processing_complete = pyqtSignal(object)
    processing_error = pyqtSignal(str)
    translation_warning = pyqtSignal(str, object)

    # 类级别共享的模型（避免重复加载）
    _shared_model = None

    def __init__(self, file_path: str, source_lang: str, target_lang: str):
        super().__init__()
        self.file_path = file_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._audio_processor = AudioProcessor()
        self._speech_recognizer = SpeechRecognizer(model_size="medium")  # 更大的模型，识别更准确
        self._translator = Translator()

    @classmethod
    def preload_whisper_model(cls):
        """在主线程预加载 Whisper 模型"""
        if cls._shared_model is None:
            import whisper
            cls._shared_model = whisper.load_model("medium")
        return cls._shared_model

    def run(self):
        try:
            self.progress_updated.emit(0.05, "正在加载音频文件…")
            audio_data = self._audio_processor.load_file(self.file_path)

            self.progress_updated.emit(0.1, "正在进行语音识别…")

            # 使用预加载的模型
            if ProcessingWorker._shared_model is not None:
                self._speech_recognizer._model = ProcessingWorker._shared_model

            def recognition_progress(p: float):
                overall = 0.1 + p * 0.6
                self.progress_updated.emit(overall, "正在进行语音识别…")

            self._speech_recognizer.set_progress_callback(recognition_progress)
            segments = self._speech_recognizer.recognize(audio_data, self.source_lang)

            if not segments:
                self.processing_error.emit("未识别到语音内容")
                return

            self.progress_updated.emit(0.75, "正在翻译…")
            translations = self._translator.translate_batch(
                segments, self.source_lang, self.target_lang
            )

            self.progress_updated.emit(0.95, "正在准备显示…")
            manager = SubtitleManager(translations)

            self.progress_updated.emit(1.0, "处理完成")
            self.processing_complete.emit(manager)

        except (AudioProcessorError, SpeechRecognizerError, TranslatorError) as e:
            self.processing_error.emit(str(e))
        except Exception as e:
            self.processing_error.emit(f"处理失败: {e}")


# =========================
# 主窗口
# =========================
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._worker: Optional[ProcessingWorker] = None
        self._subtitle_manager: Optional[SubtitleManager] = None
        # 缓存每个文件的字幕数据 {file_path: SubtitleManager}
        self._subtitle_cache: Dict[str, SubtitleManager] = {}
        # 是否正在自动处理队列
        self._auto_processing = False
        self._setup_ui()
        self._connect_signals()
        
        # 在主线程预加载 Whisper 模型
        ProcessingWorker.preload_whisper_model()

    # ---------- UI ----------
    def _setup_ui(self):
        self.setWindowTitle("音频翻译软件")
        self.resize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._setup_header(main_layout)
        self._setup_center(main_layout)
        self._setup_bottom(main_layout)

    # Style constants for consistent theming (Requirements 4.1)
    PRIMARY_COLOR = "#1DB954"
    PRIMARY_HOVER = "#1ED760"
    
    def _setup_header(self, parent):
        frame = QFrame()
        frame.setFixedHeight(60)
        frame.setStyleSheet("background:#fff;border-bottom:1px solid #e0e0e0;")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("🎵 音频翻译")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{self.PRIMARY_COLOR};")
        layout.addWidget(title)

        layout.addStretch()
        self.language_selector = LanguageSelector()
        layout.addWidget(self.language_selector)

        self.direction_label = QLabel()
        self.direction_label.setFont(QFont("Microsoft YaHei", 12))
        layout.addWidget(self.direction_label)
        self._update_direction_label()

        parent.addWidget(frame)

    def _setup_center(self, parent):
        container = QFrame()
        container.setStyleSheet("background:#fafafa;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # ===== 进度条 =====
        self.progress_frame = QFrame()
        p_layout = QVBoxLayout(self.progress_frame)
        p_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_label = QLabel("准备处理…")
        self.progress_label.setFont(QFont("Microsoft YaHei", 12))
        p_layout.addWidget(self.progress_label)

        # Progress bar with consistent primary color (Requirements 4.1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(400)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #E0E0E0;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {self.PRIMARY_COLOR};
                border-radius: 4px;
            }}
        """)
        p_layout.addWidget(self.progress_bar)

        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)

        # ===== 字幕 =====
        self.subtitle_view = SubtitleView()
        self.subtitle_view.setVisible(False)
        layout.addWidget(self.subtitle_view, 1)

        # ===== 占位提示（关键修复点）=====
        self.placeholder_frame = QFrame()
        ph_layout = QVBoxLayout(self.placeholder_frame)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("请选择音频文件开始处理")
        label.setFont(QFont("Microsoft YaHei", 14))
        label.setStyleSheet("color:#aaaaaa;")
        ph_layout.addWidget(label)

        layout.addWidget(self.placeholder_frame)

        parent.addWidget(container, 1)

    def _setup_bottom(self, parent):
        frame = QFrame()
        frame.setStyleSheet("background:#fff;border-top:1px solid #e0e0e0;")
        layout = QVBoxLayout(frame)

        self.audio_player = AudioPlayer()
        self.audio_player.setVisible(False)
        layout.addWidget(self.audio_player)

        # 底部工具栏：文件队列 + 导出按钮
        bottom_bar = QHBoxLayout()
        
        # FileQueue replaces FileSelector (Requirements 1.3, 3.1)
        self.file_queue = FileQueueWidget()
        bottom_bar.addWidget(self.file_queue, 1)
        
        # 导出按钮（右下角）
        self.export_button = QPushButton("📄 导出字幕")
        self.export_button.setFixedHeight(40)
        self.export_button.setFont(QFont("Microsoft YaHei", 10))
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                color: #333333;
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
                border-color: #1DB954;
            }
            QPushButton:disabled {
                background-color: #F8F8F8;
                color: #AAAAAA;
            }
        """)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export_clicked)
        bottom_bar.addWidget(self.export_button)
        
        layout.addLayout(bottom_bar)

        parent.addWidget(frame)

    # ---------- 信号 ----------
    def _connect_signals(self):
        # FileQueue signals (Requirements 1.3, 3.1)
        self.file_queue.file_selected.connect(self._on_file_selected)
        # 当队列变化时（添加新文件），自动开始处理
        self.file_queue.queue_changed.connect(self._on_queue_changed)
        
        self.language_selector.language_changed.connect(
            lambda *_: self._update_direction_label()
        )
        self.audio_player.position_changed.connect(
            self.subtitle_view.set_current_time
        )
        # Connect subtitle click to audio player seek (Requirements 5.1, 5.2)
        self.subtitle_view.subtitle_clicked.connect(self._on_subtitle_clicked)
        
        # Connect playback finished for automatic sequential playback (Requirements 6.1, 6.2)
        self.audio_player.playback_finished.connect(self._on_playback_finished)

    # ---------- 状态切换 ----------
    def _show_progress(self):
        self.placeholder_frame.setVisible(False)
        self.subtitle_view.setVisible(False)
        self.audio_player.setVisible(False)
        self.progress_frame.setVisible(True)
        self.progress_bar.setValue(0)

    def _show_result(self):
        self.progress_frame.setVisible(False)
        self.placeholder_frame.setVisible(False)
        self.subtitle_view.setVisible(True)
        self.audio_player.setVisible(True)

    # ---------- 逻辑 ----------
    def _on_file_selected(self, file_path: str):
        """
        Handle file selection from queue.
        If file is already processed, load from cache. Otherwise process it.
        """
        # 检查缓存中是否已有该文件的字幕
        if file_path in self._subtitle_cache:
            # 从缓存加载，不需要重新处理
            self._load_from_cache(file_path)
        else:
            # 需要处理
            self._start_processing(file_path)
    
    def _load_from_cache(self, file_path: str):
        """从缓存加载已处理的文件"""
        manager = self._subtitle_cache[file_path]
        self.subtitle_view.set_subtitles(manager)
        self.audio_player.load_file(file_path)
        self._show_result()
        # 启用导出按钮
        self.export_button.setEnabled(True)
    
    def _on_queue_changed(self, file_paths: list):
        """
        当队列变化时（添加新文件），自动开始处理未处理的文件
        """
        if not self._auto_processing and file_paths:
            self._start_auto_processing()
    
    def _start_auto_processing(self):
        """开始自动处理队列中所有未处理的文件"""
        # 找到第一个未处理的文件
        for i, item in enumerate(self.file_queue.items):
            if item.file_path not in self._subtitle_cache:
                self._auto_processing = True
                self.file_queue.set_current_index(i)
                self._start_processing(item.file_path)
                return
        
        # 所有文件都已处理
        self._auto_processing = False
    
    def _start_processing(self, file_path: str):
        """
        Start processing a file.
        
        Requirements 6.4: When a user clicks on a file in the queue,
        switch to that file immediately.
        """
        # Stop current playback (Requirements 6.4)
        self.audio_player.stop()
        
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._show_progress()
        
        # Set file state to PROCESSING (Requirements 6.3)
        current_idx = self.file_queue.current_index
        self.file_queue.set_file_state(current_idx, FileState.PROCESSING)

        self._worker = ProcessingWorker(
            file_path,
            self.language_selector.source_language,
            self.language_selector.target_language
        )

        self._worker.progress_updated.connect(
            lambda p, m: (
                self.progress_bar.setValue(int(p * 100)),
                self.progress_label.setText(m)
            )
        )
        self._worker.processing_complete.connect(self._on_complete)
        self._worker.processing_error.connect(self._on_error)
        self._worker.translation_warning.connect(self._on_translation_warning)
        self._worker.start()

    def _on_translation_warning(self, msg: str, manager: SubtitleManager):
        """Handle translation warning - show original text when translation fails."""
        self.subtitle_view.set_subtitles(manager)
        self.audio_player.load_file(self.file_queue.current_file)
        self._show_result()
        QMessageBox.warning(self, "翻译警告", msg)

    def _on_complete(self, manager: SubtitleManager):
        current_file = self.file_queue.current_file
        
        # 缓存字幕数据
        if current_file:
            self._subtitle_cache[current_file] = manager
        
        self.subtitle_view.set_subtitles(manager)
        self.audio_player.load_file(current_file)
        self._show_result()
        
        # 启用导出按钮
        self.export_button.setEnabled(True)
        
        # Set file state to READY (Requirements 6.3)
        current_idx = self.file_queue.current_index
        self.file_queue.set_file_state(current_idx, FileState.READY)
        
        # 如果是自动处理模式，继续处理下一个未处理的文件
        if self._auto_processing:
            self._process_next_unprocessed()

    def _on_error(self, msg: str):
        self.progress_frame.setVisible(False)
        self.placeholder_frame.setVisible(True)
        QMessageBox.critical(self, "错误", msg)
        
        # 如果是自动处理模式，跳过当前文件继续处理下一个
        if self._auto_processing:
            self._process_next_unprocessed()
    
    def _process_next_unprocessed(self):
        """处理下一个未处理的文件"""
        # 找到下一个未处理的文件
        for i, item in enumerate(self.file_queue.items):
            if item.file_path not in self._subtitle_cache:
                self.file_queue.set_current_index(i)
                self._start_processing(item.file_path)
                return
        
        # 所有文件都已处理完成
        self._auto_processing = False

    def _update_direction_label(self):
        self.direction_label.setText(
            f"翻译方向: {self.language_selector.get_language_direction_text()}"
        )

    def _on_subtitle_clicked(self, index: int, start_time: float):
        """
        Handle subtitle click to seek audio player.
        
        Requirements 5.1: Seek to the start time of the clicked subtitle
        Requirements 5.2: Begin playback from that position
        """
        self.audio_player.seek(start_time)
        self.audio_player.play()

    def _on_playback_finished(self):
        """
        Handle playback finished - automatically play next file in queue.
        
        Requirements 6.1: Automatically start processing and playing the next file
        Requirements 6.2: Display completion message when last file finishes
        """
        # Mark current file as completed
        current_idx = self.file_queue.current_index
        self.file_queue.set_file_state(current_idx, FileState.COMPLETED)
        
        # Check if there's a next file
        next_file = self.file_queue.get_next_file()
        
        if next_file:
            # Start processing the next file
            self._start_processing(next_file)
        else:
            # Queue finished - show completion message
            QMessageBox.information(self, "播放完成", "所有文件已播放完毕。")
    
    def _on_export_clicked(self):
        """处理导出按钮点击"""
        current_file = self.file_queue.current_file
        if not current_file or current_file not in self._subtitle_cache:
            QMessageBox.warning(self, "提示", "请先处理音频文件")
            return
        
        manager = self._subtitle_cache[current_file]
        
        # 获取默认文件名（不含扩展名）
        default_name = os.path.splitext(os.path.basename(current_file))[0]
        
        dialog = ExportDialog(manager, default_name, current_file, self)
        dialog.exec()

    def closeEvent(self, event):
        """Handle window close event."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        self.audio_player.stop()
        event.accept()


# =========================
# 入口
# =========================
def main():
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

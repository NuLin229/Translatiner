"""
ExportDialog - Dialog for exporting subtitles to text file.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QFileDialog, QLineEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os

from src.services.subtitle_manager import SubtitleManager


class ExportDialog(QDialog):
    """导出字幕对话框"""
    
    def __init__(self, subtitle_manager: SubtitleManager, default_name: str = "subtitle", 
                 audio_file_path: str = "", parent=None):
        super().__init__(parent)
        self._manager = subtitle_manager
        self._default_name = default_name
        self._audio_file_path = audio_file_path  # 音频文件路径
        self._export_path = ""
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("导出字幕")
        self.setFixedSize(450, 280)
        self.setStyleSheet("background-color: #FAFAFA;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("📝 导出字幕文件")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1DB954;")
        layout.addWidget(title)
        
        # 导出内容选择
        content_group = QGroupBox("导出内容")
        content_group.setFont(QFont("Microsoft YaHei", 10))
        content_layout = QVBoxLayout(content_group)
        
        self.check_time = QCheckBox("时间段")
        self.check_time.setChecked(True)
        self.check_time.setEnabled(False)  # 时间段始终导出
        content_layout.addWidget(self.check_time)
        
        self.check_original = QCheckBox("原文")
        self.check_original.setChecked(True)
        content_layout.addWidget(self.check_original)
        
        self.check_translated = QCheckBox("译文")
        self.check_translated.setChecked(True)
        content_layout.addWidget(self.check_translated)
        
        layout.addWidget(content_group)
        
        # 保存路径
        path_layout = QHBoxLayout()
        path_label = QLabel("保存位置:")
        path_label.setFont(QFont("Microsoft YaHei", 10))
        path_layout.addWidget(path_label)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("点击浏览选择保存位置...")
        self.path_edit.setReadOnly(True)
        self.path_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background: white;
            }
        """)
        path_layout.addWidget(self.path_edit, 1)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        browse_btn.clicked.connect(self._on_browse)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        export_btn = QPushButton("导出")
        export_btn.setFixedWidth(80)
        export_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
        """)
        export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_browse(self):
        """选择保存路径"""
        # 默认保存到音频文件所在目录的"导出内容"文件夹
        if self._audio_file_path and os.path.exists(self._audio_file_path):
            audio_dir = os.path.dirname(self._audio_file_path)
            export_dir = os.path.join(audio_dir, "导出内容")
            # 自动创建导出文件夹
            if not os.path.exists(export_dir):
                try:
                    os.makedirs(export_dir)
                except:
                    export_dir = audio_dir
        else:
            # 备用：使用桌面
            export_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(export_dir):
                export_dir = os.path.expanduser("~")
        
        default_path = os.path.join(export_dir, self._default_name + ".txt")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存字幕文件",
            default_path,
            "文本文件 (*.txt)",
            options=QFileDialog.Option.DontUseNativeDialog  # 使用Qt对话框，更快
        )
        if file_path:
            self._export_path = file_path
            self.path_edit.setText(file_path)
    
    def _on_export(self):
        """执行导出"""
        # 检查是否选择了保存路径
        if not self._export_path:
            QMessageBox.warning(self, "提示", "请先选择保存位置")
            return
        
        # 检查是否至少选择了一项内容
        if not self.check_original.isChecked() and not self.check_translated.isChecked():
            QMessageBox.warning(self, "提示", "请至少选择导出原文或译文")
            return
        
        try:
            self._do_export()
            QMessageBox.information(self, "成功", f"字幕已导出到:\n{self._export_path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def _do_export(self):
        """执行实际的导出操作"""
        include_original = self.check_original.isChecked()
        include_translated = self.check_translated.isChecked()
        
        lines = []
        for segment in self._manager.segments:
            # 时间段
            time_str = f"{segment.format_start_time()} - {segment.format_end_time()}"
            lines.append(time_str)
            
            # 原文
            if include_original:
                lines.append(segment.original_text)
            
            # 译文（如果与原文不同）
            if include_translated:
                if segment.translated_text != segment.original_text:
                    lines.append(segment.translated_text)
                elif not include_original:
                    # 如果只导出译文但译文和原文相同，也要输出
                    lines.append(segment.translated_text)
            
            # 空行分隔
            lines.append("")
        
        # 写入文件
        with open(self._export_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

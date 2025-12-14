"""
LanguageSelector - Language selection component for audio translator.

Implements source and target language selection with:
- Source language dropdown (Japanese, English, Korean, Chinese)
- Target language dropdown
- Auto-default target to Chinese for non-Chinese sources
- Language preference persistence
"""

import json
import os
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from src.models.data_models import LanguageConfig


class LanguageSelector(QWidget):
    """
    Language selection widget for source and target languages.
    
    Features:
    - Source language dropdown (ja, en, ko, zh)
    - Target language dropdown
    - Auto-default target to Chinese for non-Chinese sources
    - Language preference persistence
    """
    
    # Signal emitted when language selection changes
    language_changed = pyqtSignal(str, str)  # source_lang, target_lang
    
    # Supported languages mapping
    SUPPORTED_LANGUAGES = {
        'ja': '日语',
        'en': '英语',
        'ko': '韩语',
        'zh': '中文'
    }
    
    # Default preferences file path
    DEFAULT_PREFS_PATH = os.path.join(
        os.path.expanduser('~'), '.audio_translator_prefs.json'
    )
    
    def __init__(self, prefs_path: Optional[str] = None, parent=None):
        """
        Initialize the language selector.
        
        Args:
            prefs_path: Optional path for preferences file. If None, uses default.
            parent: Parent widget
        """
        super().__init__(parent)
        self._prefs_path = prefs_path or self.DEFAULT_PREFS_PATH
        self._source_lang = 'ja'  # Default source language
        self._target_lang = 'zh'  # Default target language
        self._updating = False  # Flag to prevent recursive updates
        self._setup_ui()
        self._load_preferences()
    
    def _setup_ui(self):
        """Set up the UI components."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(20)
        
        # Source language section
        source_layout = QVBoxLayout()
        source_layout.setSpacing(5)
        
        source_label = QLabel("源语言")
        source_label.setStyleSheet("font-weight: bold; color: #333;")
        source_layout.addWidget(source_label)
        
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(120)
        for code, name in self.SUPPORTED_LANGUAGES.items():
            self.source_combo.addItem(name, code)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_layout.addWidget(self.source_combo)
        
        main_layout.addLayout(source_layout)
        
        # Arrow indicator
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 20px; color: #666;")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(arrow_label)
        
        # Target language section
        target_layout = QVBoxLayout()
        target_layout.setSpacing(5)
        
        target_label = QLabel("目标语言")
        target_label.setStyleSheet("font-weight: bold; color: #333;")
        target_layout.addWidget(target_label)
        
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(120)
        for code, name in self.SUPPORTED_LANGUAGES.items():
            self.target_combo.addItem(name, code)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        target_layout.addWidget(self.target_combo)
        
        main_layout.addLayout(target_layout)
        
        # Add stretch to push everything to the left
        main_layout.addStretch(1)
        
        # Set initial selection
        self._set_combo_by_code(self.source_combo, self._source_lang)
        self._set_combo_by_code(self.target_combo, self._target_lang)
    
    def _set_combo_by_code(self, combo: QComboBox, code: str):
        """Set combo box selection by language code."""
        for i in range(combo.count()):
            if combo.itemData(i) == code:
                combo.setCurrentIndex(i)
                break
    
    def _on_source_changed(self, index: int):
        """Handle source language change."""
        if self._updating:
            return
        
        self._updating = True
        try:
            new_source = self.source_combo.itemData(index)
            if new_source != self._source_lang:
                self._source_lang = new_source
                
                # Auto-set target to Chinese for non-Chinese sources
                if new_source != 'zh':
                    self._target_lang = 'zh'
                    self._set_combo_by_code(self.target_combo, 'zh')
                
                self._save_preferences()
                self.language_changed.emit(self._source_lang, self._target_lang)
        finally:
            self._updating = False
    
    def _on_target_changed(self, index: int):
        """Handle target language change."""
        if self._updating:
            return
        
        self._updating = True
        try:
            new_target = self.target_combo.itemData(index)
            if new_target != self._target_lang:
                self._target_lang = new_target
                self._save_preferences()
                self.language_changed.emit(self._source_lang, self._target_lang)
        finally:
            self._updating = False
    
    def _load_preferences(self):
        """Load language preferences from file."""
        try:
            if os.path.exists(self._prefs_path):
                with open(self._prefs_path, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                    
                    source = prefs.get('source_language', 'ja')
                    target = prefs.get('target_language', 'zh')
                    
                    # Validate loaded values
                    if source in self.SUPPORTED_LANGUAGES:
                        self._source_lang = source
                    if target in self.SUPPORTED_LANGUAGES:
                        self._target_lang = target
                    
                    # Update UI
                    self._updating = True
                    self._set_combo_by_code(self.source_combo, self._source_lang)
                    self._set_combo_by_code(self.target_combo, self._target_lang)
                    self._updating = False
        except (json.JSONDecodeError, IOError):
            # Use defaults if file is corrupted or unreadable
            pass
    
    def _save_preferences(self):
        """Save language preferences to file."""
        try:
            prefs = {
                'source_language': self._source_lang,
                'target_language': self._target_lang
            }
            with open(self._prefs_path, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except IOError:
            # Silently fail if unable to save
            pass
    
    @property
    def source_language(self) -> str:
        """Get the currently selected source language code."""
        return self._source_lang
    
    @property
    def target_language(self) -> str:
        """Get the currently selected target language code."""
        return self._target_lang
    
    def set_source_language(self, code: str):
        """
        Set the source language programmatically.
        
        Args:
            code: Language code (ja, en, ko, zh)
        """
        if code in self.SUPPORTED_LANGUAGES and code != self._source_lang:
            self._source_lang = code
            self._updating = True
            self._set_combo_by_code(self.source_combo, code)
            self._updating = False
            
            # Auto-set target to Chinese for non-Chinese sources
            if code != 'zh' and self._target_lang != 'zh':
                self._target_lang = 'zh'
                self._updating = True
                self._set_combo_by_code(self.target_combo, 'zh')
                self._updating = False
            
            self._save_preferences()
            self.language_changed.emit(self._source_lang, self._target_lang)
    
    def set_target_language(self, code: str):
        """
        Set the target language programmatically.
        
        Args:
            code: Language code (ja, en, ko, zh)
        """
        if code in self.SUPPORTED_LANGUAGES and code != self._target_lang:
            self._target_lang = code
            self._updating = True
            self._set_combo_by_code(self.target_combo, code)
            self._updating = False
            self._save_preferences()
            self.language_changed.emit(self._source_lang, self._target_lang)
    
    def get_language_config(self) -> LanguageConfig:
        """
        Get the current language configuration.
        
        Returns:
            LanguageConfig with current source and target languages
        """
        return LanguageConfig(
            source_language=self._source_lang,
            target_language=self._target_lang
        )
    
    def get_language_direction_text(self) -> str:
        """
        Get a human-readable language direction string.
        
        Returns:
            String like "日语 → 中文" representing the translation direction
        """
        source_name = self.SUPPORTED_LANGUAGES.get(self._source_lang, self._source_lang)
        target_name = self.SUPPORTED_LANGUAGES.get(self._target_lang, self._target_lang)
        return f"{source_name} → {target_name}"
    
    def get_default_target_for_source(self, source_lang: str) -> str:
        """
        Get the default target language for a given source language.
        
        For non-Chinese sources, returns 'zh' (Chinese).
        For Chinese source, returns 'zh' (same language, no translation).
        
        Args:
            source_lang: Source language code
            
        Returns:
            Default target language code
        """
        if source_lang != 'zh':
            return 'zh'
        return 'zh'

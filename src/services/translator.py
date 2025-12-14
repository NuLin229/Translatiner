import json
import urllib.request
import re
from typing import List, Dict
from src.models.data_models import TranscriptSegment, TranslationSegment


class TranslatorError(Exception):
    pass


class Translator:
    """
    AI Translator using local Qwen (Ollama).
    No content filter. Fully offline.
    """

    LANG_NAMES = {
        'ja': '日语',
        'en': '英语',
        'ko': '韩语',
        'zh': '中文'
    }

    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434/api/generate",
        model: str = "qwen2.5:3b"  # 3b 平衡翻译质量和内存占用
    ):
        self.ollama_url = ollama_url
        self.model = model


    # ==============================
    # 核心：调用 Ollama（带重试）
    # ==============================
    def _call_ollama(self, prompt: str, max_retries: int = 3) -> str:
        import time
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    self.ollama_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    # 每次成功调用后稍微等待，避免过载
                    time.sleep(0.5)
                    return result.get("response", "").strip()
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    time.sleep(wait_time)
                else:
                    raise TranslatorError(f"Ollama 调用失败: {e}")

    def should_translate(self, source_lang: str, target_lang: str) -> bool:
        return source_lang != target_lang

    # ==============================
    # 批量翻译（分批处理，避免文本过长）
    # ==============================
    def translate_batch(
        self,
        segments: List[TranscriptSegment],
        source_lang: str,
        target_lang: str
    ) -> List[TranslationSegment]:

        if not segments:
            return []

        if not self.should_translate(source_lang, target_lang):
            return [
                TranslationSegment(
                    start_time=s.start_time,
                    end_time=s.end_time,
                    original_text=s.text,
                    translated_text=s.text,
                    source_language=source_lang,
                    target_language=target_lang
                ) for s in segments
            ]

        # 分批处理，每批最多10个片段
        BATCH_SIZE = 10
        all_results = []
        
        for batch_start in range(0, len(segments), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(segments))
            batch_segments = segments[batch_start:batch_end]
            
            batch_results = self._translate_single_batch(
                batch_segments, source_lang, target_lang, batch_start
            )
            all_results.extend(batch_results)
        
        return all_results

    def _translate_single_batch(
        self,
        segments: List[TranscriptSegment],
        source_lang: str,
        target_lang: str,
        offset: int = 0
    ) -> List[TranslationSegment]:
        """翻译单个批次"""
        numbered = []
        for i, seg in enumerate(segments):
            text = seg.text.strip()
            if text:
                numbered.append(f"[{i+1}] {text}")

        combined_text = "\n".join(numbered)

        source_name = self.LANG_NAMES.get(source_lang, source_lang)
        target_name = self.LANG_NAMES.get(target_lang, target_lang)

        prompt = f"""将下面的{source_name}翻译成{target_name}，保留[编号]：

{combined_text}

翻译结果："""

        try:
            translated_text = self._call_ollama(prompt)
            parsed = self._parse_numbered_text(translated_text, len(segments))
        except TranslatorError as e:
            print(f"[翻译错误] {e}")
            parsed = {}

        result = []
        for i, seg in enumerate(segments):
            translated = parsed.get(i + 1, seg.text)
            result.append(
                TranslationSegment(
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    original_text=seg.text,
                    translated_text=translated,
                    source_language=source_lang,
                    target_language=target_lang
                )
            )

        return result

    # ==============================
    # 编号解析（你原来的逻辑，保留）
    # ==============================
    def _parse_numbered_text(self, text: str, expected: int) -> Dict[int, str]:
        result = {}
        pattern = r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        for n, content in matches:
            try:
                result[int(n)] = content.strip()
            except ValueError:
                pass

        if len(result) < expected:
            lines = text.splitlines()
            for line in lines:
                m = re.match(r'\[(\d+)\]\s*(.+)', line)
                if m:
                    idx = int(m.group(1))
                    if idx not in result:
                        result[idx] = m.group(2).strip()

        return result

    # ==============================
    # 单句翻译（可用于 UI）
    # ==============================
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not self.should_translate(source_lang, target_lang):
            return text

        source_name = self.LANG_NAMES.get(source_lang, source_lang)
        target_name = self.LANG_NAMES.get(target_lang, target_lang)

        prompt = f"""
请将下面的{source_name}翻译成自然的{target_name}，
并修正口语或不通顺的地方（不要扩写）：

{text}
"""

        try:
            return self._call_ollama(prompt)
        except TranslatorError:
            return text

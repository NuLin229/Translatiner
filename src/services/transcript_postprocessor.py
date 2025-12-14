import json
import urllib.request
from typing import List

from src.models.data_models import TranscriptSegment


class TranscriptPostProcessorError(Exception):
    pass


class TranscriptPostProcessor:
    """
    Use local Qwen (Ollama) to polish ASR transcripts
    without changing timing or meaning.
    """

    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434/api/generate",
        model: str = "qwen2.5:1.5b"
    ):
        self.ollama_url = ollama_url
        self.model = model
        print(f"[INFO] Transcript 校对模型: {model}")

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            self.ollama_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "").strip()
        except Exception as e:
            raise TranscriptPostProcessorError(str(e))

    # ==============================
    # 对外接口
    # ==============================
    def polish(
        self,
        segments: List[TranscriptSegment]
    ) -> List[TranscriptSegment]:
        """
        Polish transcript text only.
        Timing & segment count MUST remain unchanged.
        """

        if not segments:
            return []

        numbered = []
        for i, seg in enumerate(segments):
            text = seg.text.strip()
            if text:
                numbered.append(f"[{i+1}] {text}")

        combined_text = "\n".join(numbered)

        lang = segments[0].language

        prompt = f"""
你是一个语音识别文本校对专家。

规则：
1. 只修正明显的 ASR 错误、助词错误、断句错误
2. 不改变原意
3. 不扩写、不总结
4. 不翻译
5. 严格保留 [编号]，数量和顺序不能变

原文（{lang}）：
{combined_text}
"""

        corrected_text = self._call_ollama(prompt)
        parsed = self._parse_numbered_text(corrected_text, len(segments))

        result = []
        for i, seg in enumerate(segments):
            new_text = parsed.get(i + 1, seg.text)
            result.append(
                TranscriptSegment(
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=new_text,
                    language=seg.language
                )
            )

        return result

    # ==============================
    # 编号解析（与 Translator 同款）
    # ==============================
    def _parse_numbered_text(self, text: str, expected: int):
        import re

        result = {}
        pattern = r'\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        for n, content in matches:
            try:
                result[int(n)] = content.strip()
            except ValueError:
                pass

        if len(result) < expected:
            for line in text.splitlines():
                m = re.match(r'\[(\d+)\]\s*(.+)', line)
                if m:
                    idx = int(m.group(1))
                    if idx not in result:
                        result[idx] = m.group(2).strip()

        return result

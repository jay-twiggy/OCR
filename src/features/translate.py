"""번역 기능.

`deep-translator`의 GoogleTranslator(무료 웹 백엔드, API 키 불필요)를 사용한다.
대용량 텍스트는 4500자 청크로 나눠 차례로 번역 후 결합.

향후 DeepL/Papago API를 추가할 때를 대비해 함수형 인터페이스로 시작.
실패 시 예외를 던지고, 호출자(워커 스레드)가 처리.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# 사용자에게 보여줄 언어 라벨. (드롭다운에 표시되는 순서 — 자주 쓰는 한/영/중/일 우선)
LANG_LABELS: dict[str, str] = {
    "ko": "한국어",
    "en": "영어",
    "zh-CN": "중국어(간체)",
    "ja": "일본어",
    "zh-TW": "중국어(번체)",
    "es": "스페인어",
    "fr": "프랑스어",
    "de": "독일어",
    "vi": "베트남어",
    "ru": "러시아어",
}

_MAX_CHUNK_CHARS = 4500  # GoogleTranslator의 5000자 제한 마진


@dataclass
class TranslationResult:
    source_lang: str   # 'auto' 또는 감지/지정 언어 코드
    target_lang: str
    text: str
    engine: str


def translate(text: str, target: str = "en", source: str = "auto") -> TranslationResult:
    """텍스트 번역. 동기. 워커 스레드에서 호출 권장.

    Args:
        text: 원문
        target: 대상 언어 코드 (LANG_LABELS 키)
        source: 원본 언어 코드 또는 'auto'

    Returns:
        TranslationResult — 번역 실패 시 빈 문자열일 수 있음.
    """
    if not text or not text.strip():
        return TranslationResult(source_lang=source, target_lang=target, text="", engine="google")

    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source=source, target=target)
    chunks = _split_text(text, _MAX_CHUNK_CHARS)
    log.info("translate: %d chunks (total %d chars) target=%s", len(chunks), len(text), target)

    parts: list[str] = []
    for i, chunk in enumerate(chunks):
        try:
            translated = translator.translate(chunk) or ""
        except Exception as exc:  # noqa: BLE001
            log.exception("translate chunk %d failed", i)
            translated = ""
        parts.append(translated)

    combined = "\n".join(parts) if len(parts) > 1 else (parts[0] if parts else "")
    return TranslationResult(
        source_lang=source,
        target_lang=target,
        text=combined,
        engine="google",
    )


def _split_text(text: str, max_chars: int) -> list[str]:
    """단락 단위로 그리디 분할. 단일 단락이 max_chars를 넘으면 해당 단락만 강제 분할."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for line in text.split("\n"):
        # 한 줄 자체가 제한을 넘으면 강제 분할
        if len(line) > max_chars:
            if buf:
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            for i in range(0, len(line), max_chars):
                chunks.append(line[i:i + max_chars])
            continue

        if buf_len + len(line) + 1 > max_chars and buf:
            chunks.append("\n".join(buf))
            buf, buf_len = [line], len(line)
        else:
            buf.append(line)
            buf_len += len(line) + 1

    if buf:
        chunks.append("\n".join(buf))
    return chunks

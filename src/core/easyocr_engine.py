"""EasyOCR 래퍼. PaddleOCR과 동일한 OCRResult 인터페이스를 노출.

PyTorch 기반의 한국어/영어 인식기. PaddleOCR과 병렬 실행해 더 나은 쪽을 채택하기 위해 사용.
첫 실행 시 모델 자동 다운로드(~80MB).

EasyOCR이 설치되어 있지 않거나 초기화에 실패하면 `EasyOCREngine.is_available()`가 False를
반환하고, recognize 호출은 빈 OCRResult로 폴백한다.
"""
from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
from PIL import Image

from .ocr_engine import OCRLine, OCRResult

log = logging.getLogger(__name__)


class EasyOCREngine:
    """싱글톤 패턴. PyTorch 모델 로딩이 무거우므로 1회만 초기화."""

    _instance: "EasyOCREngine | None" = None
    _init_failed: bool = False

    def __init__(self, langs: Iterable[str] = ("ko", "en")) -> None:
        import easyocr  # 무거운 import는 실제 초기화 시점까지 지연

        self._langs = list(langs)
        log.info("Loading EasyOCR (langs=%s)", self._langs)
        # gpu=False — CPU 강제. 첫 호출 시 모델 다운로드(~80MB)
        self._reader = easyocr.Reader(self._langs, gpu=False, verbose=False)
        log.info("EasyOCR loaded.")

    @classmethod
    def instance(cls) -> "EasyOCREngine | None":
        """초기화 실패 시 None을 반환. 호출자는 None 체크 후 폴백."""
        if cls._init_failed:
            return None
        if cls._instance is None:
            try:
                cls._instance = cls()
            except Exception as exc:  # noqa: BLE001
                log.warning("EasyOCR unavailable: %s", exc)
                cls._init_failed = True
                return None
        return cls._instance

    @classmethod
    def is_available(cls) -> bool:
        return cls.instance() is not None

    def recognize(self, image: Image.Image | np.ndarray) -> OCRResult:
        if isinstance(image, Image.Image):
            arr = np.array(image.convert("RGB"))
        else:
            arr = image

        log.info("EasyOCR recognize: input shape=%s", getattr(arr, "shape", "?"))
        try:
            raw = self._reader.readtext(arr)
        except Exception:  # noqa: BLE001
            log.exception("EasyOCR recognize failed")
            return OCRResult(lines=[])

        lines: list[OCRLine] = []
        for entry in raw:
            try:
                bbox, text, confidence = entry
            except (ValueError, TypeError):
                continue
            if not text:
                continue
            box = [(float(p[0]), float(p[1])) for p in bbox]
            lines.append(OCRLine(text=text, confidence=float(confidence), box=box))

        log.info("EasyOCR recognize: parsed %d lines", len(lines))
        return OCRResult(lines=lines)

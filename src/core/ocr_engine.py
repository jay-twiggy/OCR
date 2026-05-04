"""PaddleOCR 래퍼. 한국어+영어 혼용 모델을 사용한다.

PaddleOCR은 'korean' 모델이 한+영을 함께 인식한다.
첫 호출 시 모델이 자동 다운로드(약 10MB)되며 이후 오프라인 동작.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from PIL import Image


@dataclass
class OCRLine:
    text: str
    confidence: float
    box: list[tuple[float, float]]  # 4 points: TL, TR, BR, BL


@dataclass
class OCRResult:
    lines: list[OCRLine]

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class OCREngine:
    """싱글톤처럼 사용. PaddleOCR 인스턴스는 무거우므로 한 번만 로딩."""

    _instance: "OCREngine | None" = None

    def __init__(self, lang: str = "korean") -> None:
        from paddleocr import PaddleOCR

        self._lang = lang
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    @classmethod
    def instance(cls, lang: str = "korean") -> "OCREngine":
        if cls._instance is None or cls._instance._lang != lang:
            cls._instance = cls(lang=lang)
        return cls._instance

    def recognize(self, image: Image.Image | np.ndarray) -> OCRResult:
        if isinstance(image, Image.Image):
            arr = np.array(image.convert("RGB"))
        else:
            arr = image

        raw = self._ocr.ocr(arr, cls=True)
        return OCRResult(lines=list(_parse_paddle_result(raw)))


def _parse_paddle_result(raw) -> Iterable[OCRLine]:
    """PaddleOCR 출력은 버전에 따라 형식이 살짝 다르다. 양쪽 모두 처리."""
    if not raw:
        return
    page = raw[0] if isinstance(raw[0], list) else raw
    if page is None:
        return
    for entry in page:
        if entry is None:
            continue
        try:
            box, (text, confidence) = entry
        except (ValueError, TypeError):
            continue
        if not text:
            continue
        yield OCRLine(
            text=text,
            confidence=float(confidence),
            box=[(float(x), float(y)) for x, y in box],
        )

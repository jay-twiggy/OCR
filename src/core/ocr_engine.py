"""PaddleOCR 래퍼. 한국어+영어 혼용 모델을 사용한다.

PaddleOCR 'korean' 모델이 한+영을 함께 인식한다.
첫 호출 시 모델이 자동 다운로드되며 이후 오프라인 동작.

PaddleOCR 2.x와 3.x를 모두 지원:
- 2.x: `PaddleOCR(use_angle_cls=True, ...)` + `.ocr(arr, cls=True)` → 중첩 리스트
- 3.x: `PaddleOCR(use_textline_orientation=True, ...)` + `.predict(arr)` → dict 리스트
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

_DEBUG_DIR = Path(__file__).resolve().parents[2] / "logs"


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
        """같은 줄에 있는 박스는 공백으로 합치고, 다른 줄은 개행으로 구분.

        업스케일된 이미지에서 PaddleOCR이 단어/구절 단위로 영역을 분리하는 경향이 있어,
        Y 좌표 기준으로 동일 라인을 그룹핑하여 자연스러운 문단으로 복원한다.
        confidence가 매우 낮은(0.2 미만) 박스는 노이즈로 보고 제외.
        """
        return _format_text(self.lines)


def _format_text(lines: list[OCRLine], min_confidence: float = 0.2) -> str:
    """OCR 결과를 자연스러운 단락 구조로 복원.

    1단계: Y좌표 근접 박스를 묶어 "시각적 줄" 생성.
    2단계: 시각적 줄을 단락으로 병합. 다음 두 조건이 모두 충족될 때만 같은 단락:
      a) Y갭이 작음 (한 줄 높이의 80% 이내)
      b) 이전 줄이 "꽉 찬 줄" (우측 한계까지 도달)
    이전 줄이 짧으면 (불릿 항목, 단락 마지막 줄 등) 새 단락으로 분리.
    """
    items = [l for l in lines if l.confidence >= min_confidence and l.text.strip()]
    if not items:
        return ""

    def top_y(line: OCRLine) -> float:
        return min(p[1] for p in line.box) if line.box else 0.0

    def bottom_y(line: OCRLine) -> float:
        return max(p[1] for p in line.box) if line.box else 0.0

    def left_x(line: OCRLine) -> float:
        return min(p[0] for p in line.box) if line.box else 0.0

    def right_x(line: OCRLine) -> float:
        return max(p[0] for p in line.box) if line.box else 0.0

    def box_height(line: OCRLine) -> float:
        if not line.box:
            return 20.0
        ys = [p[1] for p in line.box]
        return max(ys) - min(ys)

    heights = [box_height(l) for l in items if l.box]
    median_h = sorted(heights)[len(heights) // 2] if heights else 20.0
    line_group_threshold = max(median_h * 0.6, 8.0)

    # Step 1: Y 근접 박스를 묶어 시각적 줄 생성.
    sorted_lines = sorted(items, key=top_y)
    line_groups: list[list[OCRLine]] = []
    for line in sorted_lines:
        if line_groups and abs(top_y(line) - top_y(line_groups[-1][0])) <= line_group_threshold:
            line_groups[-1].append(line)
        else:
            line_groups.append([line])

    visual_lines: list[dict] = []
    for group in line_groups:
        ordered = sorted(group, key=left_x)
        visual_lines.append({
            "text": " ".join(g.text for g in ordered),
            "top": min(top_y(g) for g in group),
            "bottom": max(bottom_y(g) for g in group),
            "right": max(right_x(g) for g in group),
        })

    # Step 2: 단락 병합.
    # "꽉 찬 줄" 임계값: 모든 시각적 줄 우측 끝의 최댓값 - tolerance.
    max_right = max(vl["right"] for vl in visual_lines)
    full_tolerance = max(max_right * 0.05, 30.0)
    full_line_threshold = max_right - full_tolerance

    paragraph_y_threshold = max(median_h * 0.8, 12.0)

    paragraphs: list[str] = []
    current = visual_lines[0]["text"]
    prev = visual_lines[0]
    for vl in visual_lines[1:]:
        gap = vl["top"] - prev["bottom"]
        prev_is_full = prev["right"] >= full_line_threshold
        prev_ends_thought = _ends_with_terminator(prev["text"])
        # 같은 단락 조건 3가지 모두 충족:
        # (a) Y갭 작음 (b) 이전 줄이 꽉 찬 줄 (c) 이전 줄이 종결 부호로 끝나지 않음
        same_paragraph = (
            gap <= paragraph_y_threshold
            and prev_is_full
            and not prev_ends_thought
        )
        if same_paragraph:
            current = _join_continuation(current, vl["text"])
        else:
            paragraphs.append(current)
            current = vl["text"]
        prev = vl
    paragraphs.append(current)
    return "\n".join(paragraphs)


# 종결로 간주하는 마지막 문자들: 마침표/물음표/느낌표/닫는괄호/따옴표 등.
_THOUGHT_TERMINATORS = ".!?。！？)]}」』』〕〉》｝~…"


def _ends_with_terminator(text: str) -> bool:
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in _THOUGHT_TERMINATORS


_CJK_RANGES = (
    (0xAC00, 0xD7AF),  # Hangul Syllables
    (0x4E00, 0x9FFF),  # CJK Unified
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x3400, 0x4DBF),  # CJK Ext-A
)


def _is_cjk(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _CJK_RANGES)


def _join_continuation(prev: str, curr: str) -> str:
    """줄바꿈된 같은 단락 두 줄을 자연스럽게 결합.

    - 영문 등 라틴어: 공백으로 결합 ("the boy" + "ran" → "the boy ran")
    - 한자/한글/일본어 인접: 공백 없이 결합 (단어 중간 wrap 가능성)
    - 끝이 하이픈인 경우(영문 hyphenation): 하이픈 제거 후 공백 없이 결합
    """
    if not prev:
        return curr
    if not curr:
        return prev
    last = prev[-1]
    first = curr[0]
    if last == "-":
        return prev[:-1] + curr
    if _is_cjk(last) and _is_cjk(first):
        return prev + curr
    return prev + " " + curr


class OCREngine:
    """싱글톤처럼 사용. PaddleOCR 인스턴스는 무거우므로 한 번만 로딩."""

    _instance: "OCREngine | None" = None

    def __init__(self, lang: str = "korean") -> None:
        from paddleocr import PaddleOCR

        try:
            import paddleocr
            log.info("Loading PaddleOCR (version=%s, lang=%s)", getattr(paddleocr, "__version__", "?"), lang)
        except Exception:
            log.info("Loading PaddleOCR (lang=%s)", lang)

        self._lang = lang
        self._ocr = _construct_paddle(PaddleOCR, lang)
        self._use_predict = hasattr(self._ocr, "predict")
        log.info("PaddleOCR loaded. method=%s", "predict" if self._use_predict else "ocr")

    @classmethod
    def instance(cls, lang: str = "korean") -> "OCREngine":
        if cls._instance is None or cls._instance._lang != lang:
            cls._instance = cls(lang=lang)
        return cls._instance

    def recognize(self, image: Image.Image | np.ndarray) -> OCRResult:
        if isinstance(image, Image.Image):
            arr_orig = np.array(image.convert("RGB"))
        else:
            arr_orig = image

        arr = _maybe_upscale(arr_orig)
        # 박스 좌표를 원본 이미지 공간으로 되돌리기 위한 스케일 인자
        h0, w0 = arr_orig.shape[:2]
        h1, w1 = arr.shape[:2]
        scale_x = w0 / w1 if w1 else 1.0
        scale_y = h0 / h1 if h1 else 1.0

        log.info("recognize: input shape=%s dtype=%s", getattr(arr, "shape", "?"), getattr(arr, "dtype", "?"))

        # 진단용 — OCR이 실제로 본 이미지를 디스크에 저장 (덮어쓰기, 마지막 1장만 유지).
        _save_debug_image(arr)

        if self._use_predict:
            raw = self._ocr.predict(arr)
            lines = list(_parse_v3_result(raw))
        else:
            raw = self._ocr.ocr(arr, cls=True)
            lines = list(_parse_v2_result(raw))

        # 박스를 원본 이미지 좌표로 다운스케일 (소비자는 원본 기준 좌표만 보면 됨)
        if scale_x != 1.0 or scale_y != 1.0:
            for line in lines:
                line.box = [(x * scale_x, y * scale_y) for x, y in line.box]

        log.info("recognize: parsed %d lines", len(lines))
        # 진단용 — 인식된 텍스트 미리보기와 평균 신뢰도.
        if lines:
            preview = " | ".join(line.text for line in lines[:8])
            preview = preview if len(preview) < 300 else preview[:300] + "…"
            avg_conf = sum(line.confidence for line in lines) / len(lines)
            log.info("recognize: avg_conf=%.3f preview=%s", avg_conf, preview)
        else:
            log.warning("recognize: no text recognized. raw type=%s preview=%s",
                        type(raw).__name__, _preview(raw))
        return OCRResult(lines=lines)


def _maybe_upscale(arr: np.ndarray) -> np.ndarray:
    """작은 이미지는 OCR 정확도를 위해 업스케일.

    PaddleOCR 검출 모델은 작은 글자(<24px 높이)에서 정확도가 떨어진다.
    캡처 영역의 짧은 변이 800px 미만이면 짧은 변 기준 800px이 되도록 비율 유지로 확대.
    """
    if arr.ndim < 2:
        return arr
    h, w = arr.shape[:2]
    short = min(h, w)
    if short >= 800:
        return arr
    scale = 800.0 / short
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    try:
        import cv2  # opencv-python (이미 의존성에 있음)
        upscaled = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    except Exception:
        # 폴백: PIL
        upscaled = np.array(
            Image.fromarray(arr).resize((new_w, new_h), Image.LANCZOS)
        )
    log.info("recognize: upscaled %dx%d → %dx%d (×%.2f)", w, h, new_w, new_h, scale)
    return upscaled


def _save_debug_image(arr: np.ndarray) -> None:
    try:
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = _DEBUG_DIR / "last_capture.png"
        Image.fromarray(arr).save(path)
        log.info("recognize: debug image saved → %s", path)
    except Exception:  # noqa: BLE001
        log.exception("recognize: failed to save debug image")


def _construct_paddle(PaddleOCR, lang: str):
    """PaddleOCR 생성자 호환 처리.

    PaddleOCR 3.5.0 기준으로 한국어는 server 모델이 존재하지 않음
    (`PP-OCRv5_server_rec`은 다국어 표방하나 실제로는 중국어/영어 중심으로 한국어 인식률이 떨어짐).
    따라서 `lang="korean"` + 기본 모델 = `korean_PP-OCRv5_mobile_rec` 조합이 PaddleOCR 내에서 한국어 최고 인식기.

    OneDNN 버그 회피를 위해 enable_mkldnn=False도 함께 전달.
    """
    last_err: Exception | None = None
    for kwargs in (
        {"use_textline_orientation": True, "enable_mkldnn": False, "lang": lang},
        {"use_textline_orientation": True, "lang": lang},
        {"use_angle_cls": True, "lang": lang},
        {"lang": lang},
    ):
        try:
            log.debug("Try PaddleOCR(%s)", kwargs)
            return PaddleOCR(**kwargs)
        except TypeError as exc:
            log.debug("PaddleOCR kwargs %s rejected: %s", list(kwargs), exc)
            last_err = exc
    if last_err:
        raise last_err
    raise RuntimeError("Failed to construct PaddleOCR")


def _parse_v2_result(raw) -> Iterable[OCRLine]:
    """PaddleOCR 2.x: [[ [box, (text, confidence)], ... ]]"""
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
            log.debug("Skip malformed v2 entry: %r", entry)
            continue
        if not text:
            continue
        yield OCRLine(
            text=text,
            confidence=float(confidence),
            box=[(float(x), float(y)) for x, y in box],
        )


def _parse_v3_result(raw) -> Iterable[OCRLine]:
    """PaddleOCR 3.x: predict()는 OCRResult dict-like 객체 리스트를 반환.

    각 객체는 'rec_texts', 'rec_scores', 'rec_polys'(또는 'dt_polys') 필드를 가진다.
    """
    if not raw:
        return
    for page in raw:
        texts = _field(page, "rec_texts") or []
        scores = _field(page, "rec_scores") or []
        polys = _field(page, "rec_polys") or _field(page, "dt_polys") or []
        for i, text in enumerate(texts):
            if not text:
                continue
            confidence = float(scores[i]) if i < len(scores) else 0.0
            box_arr = polys[i] if i < len(polys) else []
            try:
                box = [(float(p[0]), float(p[1])) for p in box_arr]
            except Exception:
                box = []
            yield OCRLine(text=text, confidence=confidence, box=box)


def _field(obj, name: str):
    """dict-style 또는 attribute-style 접근 모두 지원."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _preview(raw) -> str:
    s = repr(raw)
    return s if len(s) < 300 else s[:300] + "…"

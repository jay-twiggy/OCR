"""OCR 전처리.

UI 토글 없이 백그라운드에서 자동 적용. PIL.Image in / PIL.Image out.
실패 시 원본을 그대로 반환.

자동 적용:
- deskew: minAreaRect 기반 각도 추정 후 보정. 0.5° 이하 또는 20° 초과는 자동 스킵.

조건부 적용 (저신뢰 OCR 재시도 시에만, `enhance_for_retry`):
- CLAHE: 음영/조명 불균일 보정 (LAB L 채널)
- 언샤프 마스크: 흐릿한 텍스트 선명화

자동 적용하지 않는 것:
- binarize: 클린 디지털 스크린샷에서 안티앨리어싱을 깨뜨려 인식률을 떨어뜨림.
  "음영 감지" 휴리스틱이 텍스트 밀도와 잘 구분되지 않아 오작동 가능성이 큼.
  필요한 경우 _binarize() 함수를 직접 호출해서 사용.
- 색반전: OCR 엔진(`core.ocr_engine`)에서 이미 자동 처리.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


def auto(image: Image.Image) -> Image.Image:
    """자동 전처리 파이프라인. 안전한 단계만 적용."""
    try:
        arr = np.array(image.convert("RGB"))
        arr = _deskew(arr)
        return Image.fromarray(arr)
    except Exception:  # noqa: BLE001
        log.exception("preprocess failed; falling back to original image")
        return image


def enhance_for_retry(image: Image.Image) -> Image.Image:
    """저신뢰 OCR 재시도용 종합 향상: CLAHE + 약한 언샤프.

    `auto()` 가 이미 deskew 한 이미지 위에 추가 적용한다고 가정 (deskew 중복 방지).

    적용 시점: 1차 OCR 결과 신뢰도/글자수가 낮을 때만 호출됨 (`OCRWorker._maybe_retry_enhanced`).
    클린 디지털 텍스트에는 효과 미미하거나 약간 부정적이지만, 음영/흐림 이미지에는 큰 도움.
    그래서 항상 적용 X, 약한 결과일 때만 추가 시도하는 패턴.
    """
    try:
        arr = np.array(image.convert("RGB"))
        arr = _apply_clahe(arr)
        arr = _apply_unsharp(arr, amount=0.6, sigma=1.2)
        return Image.fromarray(arr)
    except Exception:  # noqa: BLE001
        log.exception("enhance_for_retry failed; falling back to original")
        return image


def _apply_clahe(arr: np.ndarray, clip_limit: float = 2.0, tile: int = 8) -> np.ndarray:
    """LAB 색공간 L 채널에 CLAHE (Contrast Limited Adaptive Histogram Equalization).

    음영/조명 불균일 캡처에서 글자-배경 대비를 국소적으로 끌어올림.
    전역 히스토그램 평활화와 달리 컬러 균형을 망가뜨리지 않음.
    """
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)


def _apply_unsharp(arr: np.ndarray, amount: float = 0.6, sigma: float = 1.2) -> np.ndarray:
    """언샤프 마스크 — 가우시안 블러와의 차이를 강조해 흐릿한 텍스트 선명화.

    amount 가 너무 크면 과도한 링잉/노이즈 증폭. 0.5~0.8이 안전 범위.
    """
    blur = cv2.GaussianBlur(arr, (0, 0), sigmaX=sigma)
    return cv2.addWeighted(arr, 1.0 + amount, blur, -amount, 0)


def _binarize(arr: np.ndarray) -> np.ndarray:
    """수동 호출용 적응형 이진화. 자동 파이프라인에서는 사용하지 않는다.

    음영이 강한 스캔본/사진에 한해 의미가 있으며, 클린 디지털 이미지에서는
    안티앨리어싱이 깨져 인식률을 오히려 낮춘다.
    """
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    bw = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31, C=10,
    )
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2RGB)


def _deskew(arr: np.ndarray) -> np.ndarray:
    """이미지 내 텍스트 박스 기반 회전 각도 추정 + 보정.

    1. 그레이스케일 + 이진화로 글자 픽셀만 추출
    2. cv2.minAreaRect로 회전 사각형 각도 계산
    3. 각도가 ±0.5° 이상이면 affine warp으로 보정
    """
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gray = cv2.bitwise_not(gray)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(bw > 0))
    if coords.size == 0:
        log.debug("deskew: no foreground pixels — skipping")
        return arr

    angle = cv2.minAreaRect(coords)[-1]
    # OpenCV의 angle은 [-90, 0) 범위. 텍스트 일반화:
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5 or abs(angle) > 20:
        log.debug("deskew: angle=%.2f out of correction range", angle)
        return arr

    h, w = arr.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    log.info("preprocess: deskewed by %.2f°", angle)
    return rotated

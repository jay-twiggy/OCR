"""OCR 전처리.

UI 토글 없이 백그라운드에서 자동 적용. PIL.Image in / PIL.Image out.
실패 시 원본을 그대로 반환.

자동 적용:
- deskew: minAreaRect 기반 각도 추정 후 보정. 0.5° 이하 또는 20° 초과는 자동 스킵.

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

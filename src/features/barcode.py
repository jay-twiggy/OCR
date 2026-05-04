"""QR / 바코드 인식.

기본은 OpenCV의 `QRCodeDetector` (이미 의존성에 있음, 시스템 DLL 불필요).
pyzbar가 import 가능하면 1D 바코드(EAN/CODE128 등)까지 함께 인식한다.
어느 쪽이든 실패 시 빈 리스트를 반환하고 OCR 본 흐름을 막지 않는다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


@dataclass
class Barcode:
    type: str   # 'QRCODE', 'EAN13', ...
    data: str   # 디코드된 문자열 (UTF-8)
    rect: tuple[int, int, int, int]  # (x, y, width, height)


def detect_barcodes(image: Image.Image) -> list[Barcode]:
    """이미지에서 모든 QR/바코드를 탐지. 예외는 던지지 않는다."""
    try:
        rgb = np.array(image.convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:  # noqa: BLE001
        log.exception("barcode: failed to prepare image")
        return []

    results: list[Barcode] = []
    results.extend(_detect_with_opencv(bgr))

    pyzbar_results = _detect_with_pyzbar(rgb)
    # OpenCV가 못 잡은 코드(주로 1D 바코드)만 추가
    seen = {(b.type, b.data) for b in results}
    for b in pyzbar_results:
        if (b.type, b.data) not in seen:
            results.append(b)

    log.info("barcode: detected %d code(s)", len(results))
    return results


def _detect_with_opencv(bgr: np.ndarray) -> list[Barcode]:
    try:
        detector = cv2.QRCodeDetector()
        ok, decoded_info, points, _ = detector.detectAndDecodeMulti(bgr)
    except Exception:  # noqa: BLE001
        log.exception("opencv QR detect failed")
        return []
    if not ok or decoded_info is None or points is None:
        return []

    results: list[Barcode] = []
    for text, pts in zip(decoded_info, points):
        if not text:
            continue
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        rect = (
            int(min(xs)),
            int(min(ys)),
            int(max(xs) - min(xs)),
            int(max(ys) - min(ys)),
        )
        results.append(Barcode(type="QRCODE", data=text, rect=rect))
    return results


def _detect_with_pyzbar(rgb: np.ndarray) -> list[Barcode]:
    try:
        from pyzbar import pyzbar
    except Exception as exc:  # noqa: BLE001
        log.debug("pyzbar unavailable: %s", exc)
        return []
    try:
        decoded = pyzbar.decode(rgb)
    except Exception:  # noqa: BLE001
        log.exception("pyzbar decode failed")
        return []

    results: list[Barcode] = []
    for d in decoded:
        try:
            text = d.data.decode("utf-8", errors="replace")
        except Exception:
            text = repr(d.data)
        rect = (int(d.rect.left), int(d.rect.top), int(d.rect.width), int(d.rect.height))
        results.append(Barcode(type=d.type, data=text, rect=rect))
    return results

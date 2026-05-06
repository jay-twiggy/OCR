"""mss 기반 화면 캡처. 다중 모니터 지원."""
from __future__ import annotations

from dataclasses import dataclass

import mss
from PIL import Image


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True)
class _ScreenMap:
    """Qt 가상 화면 logical 영역 ↔ Windows physical 영역 매핑 (모니터 1대 단위)."""
    qt_x: int       # logical
    qt_y: int
    qt_w: int
    qt_h: int
    dpr: float
    phys_x: int     # mss / Windows physical
    phys_y: int


def build_screen_mapping() -> list[_ScreenMap]:
    """각 모니터별 Qt logical 좌표 → Windows physical 좌표 매핑 테이블.

    Qt screens 와 mss monitors 를 physical 크기 기준으로 매칭. 매칭 실패 시
    동일 인덱스로 fallback. 모니터별 다른 DPR 환경에도 대응.
    """
    # PySide6 import 는 함수 안에서 (capture.py 가 GUI 없이도 import 가능하도록)
    from PySide6.QtGui import QGuiApplication

    screens = QGuiApplication.screens()
    if not screens:
        return []

    with mss.mss() as sct:
        mss_monitors = list(sct.monitors[1:])  # [0] = 가상 화면 합집합, 제외

    used = [False] * len(mss_monitors)
    mapping: list[_ScreenMap] = []
    for idx, s in enumerate(screens):
        geom = s.geometry()
        dpr = s.devicePixelRatio()
        phys_w = round(geom.width() * dpr)
        phys_h = round(geom.height() * dpr)

        # 1) physical 크기로 매칭 (가장 정확)
        matched = -1
        for i, m in enumerate(mss_monitors):
            if used[i]:
                continue
            if m["width"] == phys_w and m["height"] == phys_h:
                matched = i
                break

        # 2) fallback: 인덱스 순서
        if matched == -1 and idx < len(mss_monitors) and not used[idx]:
            matched = idx

        if matched == -1:
            continue
        used[matched] = True
        m = mss_monitors[matched]
        mapping.append(_ScreenMap(
            qt_x=geom.x(), qt_y=geom.y(),
            qt_w=geom.width(), qt_h=geom.height(),
            dpr=dpr,
            phys_x=m["left"], phys_y=m["top"],
        ))
    return mapping


def qt_logical_rect_to_physical(
    qt_x: int, qt_y: int, qt_w: int, qt_h: int,
    mapping: list[_ScreenMap] | None = None,
) -> Rect:
    """Qt 가상 화면 logical 좌표의 사각형을 Windows physical 좌표 Rect 로 변환.

    각 모서리가 속한 모니터의 DPR/원점을 사용 → 모니터별 다른 스케일에도 대응.
    매핑이 비어 있으면 변환 없이 그대로 반환 (안전 폴백).
    """
    if mapping is None:
        mapping = build_screen_mapping()
    if not mapping:
        return Rect(qt_x, qt_y, qt_w, qt_h)

    def _to_phys(lx: int, ly: int) -> tuple[int, int]:
        for m in mapping:
            if (m.qt_x <= lx < m.qt_x + m.qt_w and
                    m.qt_y <= ly < m.qt_y + m.qt_h):
                local_lx = lx - m.qt_x
                local_ly = ly - m.qt_y
                return (m.phys_x + round(local_lx * m.dpr),
                        m.phys_y + round(local_ly * m.dpr))
        # 안 잡히면 첫 모니터 DPR 로 대충 (fallback)
        m = mapping[0]
        return (m.phys_x + round((lx - m.qt_x) * m.dpr),
                m.phys_y + round((ly - m.qt_y) * m.dpr))

    px1, py1 = _to_phys(qt_x, qt_y)
    # 우/하단은 "포함" 좌표 기준으로 변환해야 동일 모니터 안에 잡힘
    px2, py2 = _to_phys(qt_x + qt_w - 1, qt_y + qt_h - 1)
    return Rect(px1, py1, max(1, px2 - px1 + 1), max(1, py2 - py1 + 1))


def capture_all_monitors() -> Image.Image:
    """모든 모니터를 합친 가상 화면 전체 캡처."""
    with mss.mss() as sct:
        monitor = sct.monitors[0]  # index 0 = 모든 모니터의 합집합
        shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_primary_monitor() -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_region(rect: Rect) -> Image.Image:
    """가상 화면 좌표계 기준 사각형 캡처."""
    if rect.width <= 0 or rect.height <= 0:
        raise ValueError(f"Invalid rect: {rect}")
    region = {"top": rect.y, "left": rect.x, "width": rect.width, "height": rect.height}
    with mss.mss() as sct:
        shot = sct.grab(region)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

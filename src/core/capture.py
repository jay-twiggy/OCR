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

"""Win/Mac 차이점을 흡수하는 유틸리티."""
from __future__ import annotations

import sys
from dataclasses import dataclass


IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


@dataclass(frozen=True)
class HotkeyBinding:
    fullscreen: str
    region: str
    browser: str
    show_window: str


def default_hotkeys() -> HotkeyBinding:
    """플랫폼별 기본 단축키. pynput 형식."""
    if IS_MAC:
        return HotkeyBinding(
            fullscreen="<cmd>+<shift>+1",
            region="<cmd>+<shift>+2",
            browser="<cmd>+<shift>+3",
            show_window="<cmd>+<shift>+0",
        )
    return HotkeyBinding(
        fullscreen="<ctrl>+<shift>+1",
        region="<ctrl>+<shift>+2",
        browser="<ctrl>+<shift>+3",
        show_window="<ctrl>+<shift>+0",
    )


def hotkey_display(binding: str) -> str:
    """pynput 형식 → 사용자에게 보여줄 문자열."""
    return (
        binding.replace("<cmd>", "Cmd")
        .replace("<ctrl>", "Ctrl")
        .replace("<shift>", "Shift")
        .replace("<alt>", "Alt")
        .replace("+", " + ")
    )

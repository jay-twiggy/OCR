"""pynput 기반 글로벌 단축키 리스너.

Mac에서는 입력 모니터링 권한이 필요(시스템 설정 > 개인정보 보호 및 보안 > 입력 모니터링).
Windows에서는 별도 권한 불필요.

pynput 콜백은 별도 스레드에서 실행되므로 Qt 위젯을 직접 만들면 안 된다.
신호(Signal)로 메인 스레드에 전달한다.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal


class HotkeyManager(QObject):
    fullscreen_pressed = Signal()
    region_pressed = Signal()
    browser_pressed = Signal()

    def __init__(self, fullscreen: str, region: str, browser: str) -> None:
        super().__init__()
        self._listener = None
        self._bindings = {
            fullscreen: self.fullscreen_pressed.emit,
            region: self.region_pressed.emit,
            browser: self.browser_pressed.emit,
        }

    def start(self) -> None:
        try:
            from pynput import keyboard
        except Exception:
            return

        try:
            self._listener = keyboard.GlobalHotKeys(
                {key: _wrap(handler) for key, handler in self._bindings.items()}
            )
            self._listener.start()
        except Exception:
            self._listener = None

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


def _wrap(handler: Callable[[], None]) -> Callable[[], None]:
    def _safe() -> None:
        try:
            handler()
        except Exception:
            pass

    return _safe

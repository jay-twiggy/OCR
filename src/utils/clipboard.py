"""클립보드 헬퍼. Qt가 살아 있을 때는 QClipboard, 아니면 pyperclip 사용."""
from __future__ import annotations


def copy_text(text: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.clipboard().setText(text)
            return
    except Exception:
        pass

    import pyperclip

    pyperclip.copy(text)

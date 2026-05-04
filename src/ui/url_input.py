"""브라우저 스크롤 OCR을 위한 URL 입력 다이얼로그."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class UrlInputDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("웹페이지 스크롤 OCR")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("OCR할 웹페이지 주소를 입력하세요:"))

        self._edit = QLineEdit(self)
        self._edit.setPlaceholderText("https://example.com")
        self._edit.setClearButtonEnabled(True)
        layout.addWidget(self._edit)

        hint = QLabel(
            "브라우저가 백그라운드에서 페이지를 열고 전체 영역을 캡처합니다.\n"
            "로그인이 필요한 페이지는 지원되지 않습니다."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._edit.setFocus(Qt.OtherFocusReason)

    def url(self) -> str:
        text = self._edit.text().strip()
        if text and "://" not in text:
            text = "https://" + text
        return text

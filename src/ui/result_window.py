"""OCR 결과 창. 좌측 캡처 이미지, 우측 인식 텍스트.

상단 툴바에 복사 / 저장 / 다시 OCR 버튼을 둠. 윈도우 스니핑 도구처럼
캡처 직후 자동으로 클립보드에도 텍스트를 복사한다.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.ocr_engine import OCREngine, OCRResult
from ..utils.clipboard import copy_text


class _OCRWorker(QThread):
    finished_ok = Signal(object)  # OCRResult
    failed = Signal(str)

    def __init__(self, image: Image.Image, lang: str = "korean") -> None:
        super().__init__()
        self._image = image
        self._lang = lang

    def run(self) -> None:
        try:
            engine = OCREngine.instance(self._lang)
            result = engine.recognize(self._image)
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ResultWindow(QMainWindow):
    def __init__(self, image: Image.Image, *, lang: str = "korean") -> None:
        super().__init__()
        self._image = image
        self._lang = lang
        self._worker: _OCRWorker | None = None

        self.setWindowTitle("SnipOCR — 결과")
        self.resize(1100, 720)
        self._build_ui()
        self._start_ocr()

    def _build_ui(self) -> None:
        toolbar = QToolBar("도구", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._copy_action = QAction("텍스트 복사", self)
        self._copy_action.triggered.connect(self._copy_text)
        toolbar.addAction(self._copy_action)

        self._save_text_action = QAction("텍스트 저장", self)
        self._save_text_action.triggered.connect(self._save_text)
        toolbar.addAction(self._save_text_action)

        self._save_image_action = QAction("이미지 저장", self)
        self._save_image_action.triggered.connect(self._save_image)
        toolbar.addAction(self._save_image_action)

        self._retry_action = QAction("다시 OCR", self)
        self._retry_action.triggered.connect(self._start_ocr)
        toolbar.addAction(self._retry_action)

        # 본문: 좌측 이미지, 우측 텍스트
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self._build_image_panel())
        splitter.addWidget(self._build_text_panel())
        splitter.setSizes([550, 550])
        self.setCentralWidget(splitter)

        # 상태바 + 진행 바
        self._status = QStatusBar(self)
        self._progress = QProgressBar(self)
        self._progress.setMaximumWidth(180)
        self._progress.setRange(0, 0)  # busy indicator
        self._progress.hide()
        self._status.addPermanentWidget(self._progress)
        self.setStatusBar(self._status)

    def _build_image_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea(panel)
        scroll.setWidgetResizable(True)

        label = QLabel(scroll)
        label.setAlignment(Qt.AlignCenter)
        pixmap = self._pil_to_pixmap(self._image)
        label.setPixmap(pixmap)
        label.setMinimumSize(1, 1)

        scroll.setWidget(label)
        layout.addWidget(scroll)
        return panel

    def _build_text_panel(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        self._text = QPlainTextEdit(panel)
        self._text.setPlaceholderText("OCR 결과가 여기에 표시됩니다…")
        layout.addWidget(self._text)

        row = QHBoxLayout()
        row.addStretch(1)
        copy_btn = QPushButton("클립보드에 복사", panel)
        copy_btn.clicked.connect(self._copy_text)
        row.addWidget(copy_btn)
        layout.addLayout(row)
        return panel

    # ── OCR 실행 ─────────────────────────────────────────────────
    def _start_ocr(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._set_busy(True, "OCR 인식 중…")
        self._text.setPlainText("")
        self._worker = _OCRWorker(self._image, self._lang)
        self._worker.finished_ok.connect(self._on_ocr_ok)
        self._worker.failed.connect(self._on_ocr_failed)
        self._worker.start()

    def _on_ocr_ok(self, result: OCRResult) -> None:
        self._set_busy(False, f"인식 완료 — {len(result.lines)} 줄")
        self._text.setPlainText(result.text)
        if result.text:
            copy_text(result.text)
            self._status.showMessage("결과를 클립보드에 복사했습니다.", 4000)

    def _on_ocr_failed(self, message: str) -> None:
        self._set_busy(False, "OCR 실패")
        QMessageBox.critical(self, "OCR 실패", message)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._progress.setVisible(busy)
        for action in (
            self._copy_action,
            self._save_text_action,
            self._retry_action,
        ):
            action.setEnabled(not busy)
        if message:
            self._status.showMessage(message)

    # ── actions ──────────────────────────────────────────────────
    def _copy_text(self) -> None:
        text = self._text.toPlainText()
        if text:
            copy_text(text)
            self._status.showMessage("텍스트를 클립보드에 복사했습니다.", 3000)

    def _save_text(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self, "텍스트 저장", "ocr_result.txt", "Text (*.txt)"
        )
        if not path_str:
            return
        Path(path_str).write_text(self._text.toPlainText(), encoding="utf-8")
        self._status.showMessage(f"저장 완료: {path_str}", 4000)

    def _save_image(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self, "이미지 저장", "capture.png", "PNG (*.png)"
        )
        if not path_str:
            return
        self._image.save(path_str, format="PNG")
        self._status.showMessage(f"저장 완료: {path_str}", 4000)

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _pil_to_pixmap(image: Image.Image) -> QPixmap:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        return pixmap

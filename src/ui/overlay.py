"""윈도우 스니핑 도구 스타일의 구역 선택 오버레이.

전체 가상 화면을 덮는 반투명 윈도우를 띄우고, 드래그로 직사각형을 선택한다.
ESC로 취소, Enter로 즉시 확정.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

from ..core.capture import Rect


@dataclass(frozen=True)
class _VirtualGeometry:
    x: int
    y: int
    width: int
    height: int


def _virtual_geometry() -> _VirtualGeometry:
    """모든 화면을 합친 가상 화면 영역 (좌상단이 0,0이 아닐 수 있음)."""
    screens = QGuiApplication.screens()
    if not screens:
        return _VirtualGeometry(0, 0, 1920, 1080)
    rect = screens[0].geometry()
    for s in screens[1:]:
        rect = rect.united(s.geometry())
    return _VirtualGeometry(rect.x(), rect.y(), rect.width(), rect.height())


class RegionOverlay(QWidget):
    """드래그로 영역을 선택하면 selected(Rect)를 emit. 취소 시 cancelled()."""

    selected = Signal(object)  # Rect (가상 화면 좌표계)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        geom = _virtual_geometry()
        self._origin = QPoint(geom.x, geom.y)
        self.setGeometry(geom.x, geom.y, geom.width, geom.height)

        self._dragging = False
        self._start: QPoint | None = None
        self._end: QPoint | None = None

    # ── lifecycle ────────────────────────────────────────────────
    def show_overlay(self) -> None:
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    # ── input ────────────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._start = event.pos()
            self._end = event.pos()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._end = event.pos()
            self._commit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._start is not None and self._end is not None:
                self._commit()

    # ── drawing ──────────────────────────────────────────────────
    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # 어두운 마스크
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self._start and self._end:
            sel = QRect(self._start, self._end).normalized()
            # 선택 영역만 투명하게
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(sel, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # 테두리
            pen = QPen(QColor(0, 122, 204), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(sel)

            # 크기 표시
            size_text = f"{sel.width()} x {sel.height()}"
            painter.setPen(QColor(255, 255, 255))
            painter.fillRect(
                sel.left(), max(0, sel.top() - 22), 110, 20, QBrush(QColor(0, 0, 0, 180))
            )
            painter.drawText(
                sel.left() + 6, max(14, sel.top() - 6), size_text
            )

    # ── helpers ──────────────────────────────────────────────────
    def _commit(self) -> None:
        if not (self._start and self._end):
            return
        local = QRect(self._start, self._end).normalized()
        if local.width() < 4 or local.height() < 4:
            self.cancelled.emit()
            self.close()
            return

        # 위젯 좌표 → 가상 화면 좌표
        global_x = local.x() + self._origin.x()
        global_y = local.y() + self._origin.y()
        rect = Rect(global_x, global_y, local.width(), local.height())
        self.selected.emit(rect)
        self.close()

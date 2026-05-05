"""사용자 피드백 위젯들 — Toast, Re-OCR 오버레이, 새 OCR 시트.

부모 위젯 위에 absolute로 떠 있는 floating UI들. 모두 dark 디자인 없이 라이트 단일.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import styles as S


# ── Toast ─────────────────────────────────────────────────────────────────────

class Toast(QFrame):
    """캡슐 모양 토스트. 부모 위젯 하단 가운데에 표시되고 자동으로 사라짐."""

    def __init__(self, parent: QWidget, text: str, duration_ms: int = 1800) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setStyleSheet(
            "QFrame#toast {"
            " background: rgba(28, 28, 30, 0.92);"
            " border-radius: 22px;"
            "}"
            "QLabel { color: white; font-size: 14px; font-weight: 500; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        check = QLabel("✓", self)
        check.setStyleSheet(f"color: {S.SYS_GREEN}; font-size: 14px; font-weight: 700;")
        layout.addWidget(check)

        msg = QLabel(text, self)
        layout.addWidget(msg)

        # subtle drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        self.adjustSize()
        self._reposition()

        # 자동 닫기
        QTimer.singleShot(duration_ms, self._fade_out)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 36
        self.move(x, max(8, y))

    def _fade_out(self) -> None:
        # Qt의 graphics effect와 QPropertyAnimation 조합으로 페이드
        self.setWindowOpacity(1.0)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(280)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(self.deleteLater)
        self._fade_anim = anim  # GC 방지
        anim.start()


def show_toast(parent: QWidget, text: str, duration_ms: int = 1800) -> Toast:
    """편의 함수: 부모에 토스트 띄우고 자동 정리."""
    toast = Toast(parent, text, duration_ms)
    toast.show()
    toast.raise_()
    return toast


# ── Re-OCR Busy Overlay ───────────────────────────────────────────────────────

class _Spinner(QWidget):
    """간단한 회전 링 스피너."""

    def __init__(self, parent: QWidget | None = None, size: int = 28) -> None:
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)  # 25fps

    def _tick(self) -> None:
        self._angle = (self._angle + 14) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(3, 3, -3, -3)
        # 옅은 베이스 링
        pen_bg = QPen(QColor(0, 0, 0, 30))
        pen_bg.setWidth(3)
        pen_bg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_bg)
        p.drawArc(rect, 0, 360 * 16)
        # 진행 호 (시작 각도 = -angle, span = 110°)
        pen_fg = QPen(QColor(S.TINT))
        pen_fg.setWidth(3)
        pen_fg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_fg)
        p.drawArc(rect, -self._angle * 16, 110 * 16)
        p.end()

    def stop(self) -> None:
        self._timer.stop()


class BusyOverlay(QWidget):
    """부모 위젯 전체를 덮는 작업 중 오버레이. 카드+스피너+라벨."""

    def __init__(self, parent: QWidget, label: str = "인식 중…") -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("BusyOverlay { background: rgba(0, 0, 0, 0.18); }")

        # 가운데 카드
        self._card = QFrame(self)
        self._card.setObjectName("busy_card")
        self._card.setStyleSheet(
            "QFrame#busy_card {"
            " background: rgba(255, 255, 255, 0.92);"
            " border-radius: 18px;"
            "}"
            f"QLabel {{ font-size: 15px; font-weight: 600; color: {S.LABEL}; }}"
        )
        card_shadow = QGraphicsDropShadowEffect(self._card)
        card_shadow.setBlurRadius(40)
        card_shadow.setOffset(0, 8)
        card_shadow.setColor(QColor(0, 0, 0, 60))
        self._card.setGraphicsEffect(card_shadow)

        layout = QHBoxLayout(self._card)
        layout.setContentsMargins(22, 16, 28, 16)
        layout.setSpacing(14)
        self._spinner = _Spinner(self._card)
        layout.addWidget(self._spinner)
        self._label = QLabel(label, self._card)
        layout.addWidget(self._label)

        self.hide()

    def show_at_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        self._card.adjustSize()
        cx = (self.width() - self._card.width()) // 2
        cy = (self.height() - self._card.height()) // 2
        self._card.move(cx, cy)
        self.show()
        self.raise_()

    def hide_overlay(self) -> None:
        self._spinner.stop()
        self.hide()
        self.deleteLater()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        if self._card:
            cx = (self.width() - self._card.width()) // 2
            cy = (self.height() - self._card.height()) // 2
            self._card.move(cx, cy)


# ── New OCR Sheet ─────────────────────────────────────────────────────────────

class NewOCRSheet(QWidget):
    """+ 새 OCR 클릭 시 표시되는 모달 시트. 2x2 그리드 옵션."""

    fullscreen_chosen = Signal()
    region_chosen = Signal()
    browser_chosen = Signal()
    file_chosen = Signal()
    cancelled = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("NewOCRSheet { background: rgba(0, 0, 0, 0.35); }")

        # 시트 컨테이너
        self._sheet = QFrame(self)
        self._sheet.setObjectName("ocr_sheet")
        self._sheet.setStyleSheet(
            "QFrame#ocr_sheet {"
            " background: rgba(250, 250, 252, 0.96);"
            f" border: 1px solid {S.SEPARATOR_LIGHT};"
            " border-radius: 22px;"
            "}"
        )
        sheet_shadow = QGraphicsDropShadowEffect(self._sheet)
        sheet_shadow.setBlurRadius(60)
        sheet_shadow.setOffset(0, 16)
        sheet_shadow.setColor(QColor(0, 0, 0, 80))
        self._sheet.setGraphicsEffect(sheet_shadow)

        sheet_layout = QVBoxLayout(self._sheet)
        sheet_layout.setContentsMargins(22, 22, 22, 18)
        sheet_layout.setSpacing(14)

        # 그래버
        grabber = QFrame(self._sheet)
        grabber.setFixedSize(36, 5)
        grabber.setStyleSheet(
            f"background: {S.LABEL_TERTIARY}; border-radius: 3px;"
        )
        grabber_row = QHBoxLayout()
        grabber_row.addStretch(1)
        grabber_row.addWidget(grabber)
        grabber_row.addStretch(1)
        sheet_layout.addLayout(grabber_row)

        # 타이틀
        title = QLabel("새 OCR", self._sheet)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {S.LABEL};")
        sheet_layout.addWidget(title)

        subtitle = QLabel("어디에서 인식할까요?", self._sheet)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"font-size: 13px; color: {S.LABEL_SECONDARY};")
        sheet_layout.addWidget(subtitle)

        # 2x2 옵션 그리드
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self._make_option("전체화면", "모든 모니터", self._on_fullscreen), 0, 0)
        grid.addWidget(self._make_option("구역", "드래그로 선택", self._on_region), 0, 1)
        grid.addWidget(self._make_option("웹페이지", "URL 풀페이지", self._on_browser), 1, 0)
        grid.addWidget(self._make_option("파일에서", "이미지 · PDF", self._on_file), 1, 1)
        sheet_layout.addLayout(grid)

        # 취소 버튼
        cancel_btn = QPushButton("취소", self._sheet)
        cancel_btn.setMinimumHeight(46)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton {"
            f" background: {S.FILL_SECONDARY};"
            f" color: {S.LABEL};"
            " border: none; border-radius: 14px;"
            " font-size: 15px; font-weight: 600;"
            "}"
            f"QPushButton:hover {{ background: {S.FILL_PRIMARY}; }}"
        )
        cancel_btn.clicked.connect(self._on_cancel)
        sheet_layout.addWidget(cancel_btn)

        self.hide()

    def _make_option(self, title: str, subtitle: str, slot: Callable[[], None]) -> QPushButton:
        btn = QPushButton(self._sheet)
        btn.setText(f"{title}\n{subtitle}")
        btn.setMinimumHeight(96)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            f" background: {S.FILL_TERTIARY};"
            f" color: {S.LABEL};"
            " border: none; border-radius: 14px;"
            " font-size: 14px; font-weight: 500;"
            " padding: 18px 8px;"
            "}"
            f"QPushButton:hover {{ background: {S.FILL_SECONDARY}; }}"
            f"QPushButton:pressed {{ background: {S.FILL_PRIMARY}; }}"
        )
        btn.clicked.connect(slot)
        return btn

    def show_at_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        self._sheet.adjustSize()
        # 시트 너비 고정 + 부모 가운데 약간 아래
        sheet_w = min(560, max(360, parent.width() - 80))
        sheet_h = self._sheet.sizeHint().height()
        self._sheet.setFixedWidth(sheet_w)
        sx = (self.width() - sheet_w) // 2
        sy = self.height() - sheet_h - 60
        self._sheet.move(sx, max(40, sy))
        self.show()
        self.raise_()

    def mousePressEvent(self, event):  # noqa: N802
        # 시트 외부 클릭 = 닫기
        if not self._sheet.geometry().contains(event.position().toPoint()):
            self._on_cancel()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        sheet_w = self._sheet.width()
        sheet_h = self._sheet.sizeHint().height()
        sx = (self.width() - sheet_w) // 2
        sy = self.height() - sheet_h - 60
        self._sheet.move(sx, max(40, sy))

    def _on_fullscreen(self) -> None:
        self.fullscreen_chosen.emit()
        self._close()

    def _on_region(self) -> None:
        self.region_chosen.emit()
        self._close()

    def _on_browser(self) -> None:
        self.browser_chosen.emit()
        self._close()

    def _on_file(self) -> None:
        self.file_chosen.emit()
        self._close()

    def _on_cancel(self) -> None:
        self.cancelled.emit()
        self._close()

    def _close(self) -> None:
        self.hide()
        self.deleteLater()

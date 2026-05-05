"""시스템 트레이 아이콘 + 메뉴."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..utils.platform_utils import default_hotkeys, hotkey_display


def _make_icon() -> QIcon:
    """간단한 폴리스 아이콘. 추후 디자인 교체 예정."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(0, 122, 204))
    painter.setPen(QColor(255, 255, 255))
    painter.drawRoundedRect(2, 2, 60, 60, 12, 12)
    painter.setFont(QFont("Arial", 22, QFont.Bold))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "OCR")
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    show_requested = Signal()
    fullscreen_requested = Signal()
    region_requested = Signal()
    browser_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(_make_icon(), parent)
        hk = default_hotkeys()
        menu = QMenu()

        show_act = QAction("창 표시", menu)
        show_act.triggered.connect(self.show_requested.emit)
        menu.addAction(show_act)

        menu.addSeparator()

        full = QAction(f"전체화면 OCR\t{hotkey_display(hk.fullscreen)}", menu)
        full.triggered.connect(self.fullscreen_requested.emit)
        menu.addAction(full)

        region = QAction(f"구역 OCR\t{hotkey_display(hk.region)}", menu)
        region.triggered.connect(self.region_requested.emit)
        menu.addAction(region)

        browser = QAction(f"웹페이지 스크롤 OCR\t{hotkey_display(hk.browser)}", menu)
        browser.triggered.connect(self.browser_requested.emit)
        menu.addAction(browser)

        menu.addSeparator()

        quit_act = QAction("종료", menu)
        quit_act.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_act)

        self.setContextMenu(menu)
        self.setToolTip("Binave OCR — 스크린샷 OCR")
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # 트레이 아이콘 클릭/더블클릭 → 메인 창 보이기 (가장 자연스러운 동작)
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_requested.emit()

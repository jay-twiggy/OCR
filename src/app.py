"""SnipOCR 메인 컨트롤러.

QApplication을 생성하고 트레이/단축키/오버레이를 연결한다.
백그라운드에서 상주하다가 사용자 트리거 시 캡처 → OCR → 결과창 표시.
"""
from __future__ import annotations

import sys

from PIL import Image
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from .core import browser_capture, capture
from .ui.overlay import RegionOverlay
from .ui.result_window import ResultWindow
from .ui.tray import TrayIcon
from .ui.url_input import UrlInputDialog
from .utils.hotkeys import HotkeyManager
from .utils.platform_utils import default_hotkeys


class _BrowserCaptureWorker(QThread):
    finished_ok = Signal(object)  # PIL.Image
    failed = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def run(self) -> None:
        try:
            image = browser_capture.capture_full_page(self._url)
            self.finished_ok.emit(image)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SnipOCRApp(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        self._qapp.setQuitOnLastWindowClosed(False)
        self._qapp.setApplicationName("SnipOCR")

        self._windows: list[ResultWindow] = []
        self._overlay: RegionOverlay | None = None
        self._browser_worker: _BrowserCaptureWorker | None = None
        self._browser_progress: QProgressDialog | None = None

        self._tray = TrayIcon()
        self._tray.fullscreen_requested.connect(self.fullscreen_ocr)
        self._tray.region_requested.connect(self.region_ocr)
        self._tray.browser_requested.connect(self.browser_ocr)
        self._tray.quit_requested.connect(self._qapp.quit)
        self._tray.show()

        hk = default_hotkeys()
        self._hotkeys = HotkeyManager(hk.fullscreen, hk.region, hk.browser)
        self._hotkeys.fullscreen_pressed.connect(self.fullscreen_ocr)
        self._hotkeys.region_pressed.connect(self.region_ocr)
        self._hotkeys.browser_pressed.connect(self.browser_ocr)
        self._hotkeys.start()

        self._tray.showMessage(
            "SnipOCR 실행 중",
            "트레이 아이콘 또는 단축키로 OCR을 실행하세요.",
            msecs=4000,
        )

    # ── 1) 전체화면 OCR ─────────────────────────────────────────
    def fullscreen_ocr(self) -> None:
        try:
            image = capture.capture_all_monitors()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(None, "캡처 실패", str(exc))
            return
        self._open_result(image)

    # ── 2) 구역 OCR ─────────────────────────────────────────────
    def region_ocr(self) -> None:
        if self._overlay is not None:
            return
        # 오버레이가 자기 자신을 캡처하지 않도록 살짝 지연
        self._overlay = RegionOverlay()
        self._overlay.selected.connect(self._on_region_selected)
        self._overlay.cancelled.connect(self._on_region_cancelled)
        self._overlay.show_overlay()

    def _on_region_selected(self, rect) -> None:
        self._overlay = None
        QTimer.singleShot(80, lambda: self._capture_region_now(rect))

    def _on_region_cancelled(self) -> None:
        self._overlay = None

    def _capture_region_now(self, rect) -> None:
        try:
            image = capture.capture_region(rect)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(None, "캡처 실패", str(exc))
            return
        self._open_result(image)

    # ── 3) 브라우저 풀페이지 OCR ────────────────────────────────
    def browser_ocr(self) -> None:
        dialog = UrlInputDialog()
        if dialog.exec() != UrlInputDialog.Accepted:
            return
        url = dialog.url()
        if not url:
            return

        self._browser_progress = QProgressDialog(
            "브라우저로 페이지를 로딩하고 캡처 중…", None, 0, 0
        )
        self._browser_progress.setWindowTitle("SnipOCR")
        self._browser_progress.setCancelButton(None)
        self._browser_progress.setMinimumDuration(0)
        self._browser_progress.show()

        self._browser_worker = _BrowserCaptureWorker(url)
        self._browser_worker.finished_ok.connect(self._on_browser_ok)
        self._browser_worker.failed.connect(self._on_browser_failed)
        self._browser_worker.start()

    def _on_browser_ok(self, image: Image.Image) -> None:
        if self._browser_progress:
            self._browser_progress.close()
            self._browser_progress = None
        self._open_result(image)

    def _on_browser_failed(self, message: str) -> None:
        if self._browser_progress:
            self._browser_progress.close()
            self._browser_progress = None
        QMessageBox.critical(
            None,
            "브라우저 캡처 실패",
            f"{message}\n\n"
            "Playwright 브라우저가 설치되지 않았다면 다음 명령을 실행하세요:\n"
            "  playwright install chromium",
        )

    # ── 결과 창 ─────────────────────────────────────────────────
    def _open_result(self, image: Image.Image) -> None:
        window = ResultWindow(image)
        window.destroyed.connect(lambda _=None, w=window: self._windows.remove(w) if w in self._windows else None)
        self._windows.append(window)
        window.show()
        window.raise_()
        window.activateWindow()

    # ── 진입점 ──────────────────────────────────────────────────
    def run(self) -> int:
        return self._qapp.exec()


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = SnipOCRApp()
    return app.run()

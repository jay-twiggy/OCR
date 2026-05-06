"""Binave OCR 메인 컨트롤러 (싱글 윈도우 모드).

QApplication을 생성하고 트레이/단축키/오버레이 + 메인 결과창 1개를 관리.
새 OCR 결과는 모두 같은 창에 로드된다 (히스토리는 좌측 사이드바로 접근).
"""
from __future__ import annotations

import logging
import sys

from PIL import Image
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog

from .core import browser_capture, capture
from .features import file_loader
from .ui.overlay import RegionOverlay
from .ui.result_window import ResultWindow
from .ui.settings_dialog import SettingsDialog
from .ui.styles import apply_app_font
from .ui.tray import TrayIcon
from .ui.url_input import UrlInputDialog
from .utils.hotkeys import HotkeyManager
from .utils.platform_utils import default_hotkeys

log = logging.getLogger(__name__)


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
            log.exception("Browser capture failed for url=%s", self._url)
            self.failed.emit(str(exc))


class BinaveOCRApp(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        self._qapp.setQuitOnLastWindowClosed(False)
        self._qapp.setApplicationName("Binave OCR")
        self._qapp.setOrganizationName("Binave OCR")
        apply_app_font(self._qapp)

        self._overlay: RegionOverlay | None = None
        self._browser_worker: _BrowserCaptureWorker | None = None
        self._browser_progress: QProgressDialog | None = None

        # 메인 윈도우 — 이미지 없이 시작 (브라우즈 모드, 히스토리만)
        self._main_window = ResultWindow(None)
        self._main_window.new_ocr_requested.connect(self._show_main_window)
        self._main_window.fullscreen_ocr_requested.connect(self.fullscreen_ocr)
        self._main_window.region_ocr_requested.connect(self.region_ocr)
        self._main_window.browser_ocr_requested.connect(self.browser_ocr)
        self._main_window.file_ocr_requested.connect(self.file_ocr)

        self._tray = TrayIcon()
        self._tray.show_requested.connect(self._show_main_window)
        self._tray.fullscreen_requested.connect(self.fullscreen_ocr)
        self._tray.region_requested.connect(self.region_ocr)
        self._tray.browser_requested.connect(self.browser_ocr)
        self._tray.settings_requested.connect(self.open_settings)
        self._tray.quit_requested.connect(self._quit_app)
        self._tray.show()

        hk = default_hotkeys()
        self._hotkeys = HotkeyManager(hk.fullscreen, hk.region, hk.browser)
        self._hotkeys.fullscreen_pressed.connect(self.fullscreen_ocr)
        self._hotkeys.region_pressed.connect(self.region_ocr)
        self._hotkeys.browser_pressed.connect(self.browser_ocr)
        self._hotkeys.start()

        self._show_main_window()

    def _show_main_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _quit_app(self) -> None:
        # 싱글 윈도우니까 closeEvent ignore가 종료를 막음 → 직접 deleteLater 후 quit
        self._main_window.deleteLater()
        self._qapp.quit()

    def open_settings(self) -> None:
        """클라우드 OCR 설정 다이얼로그. 저장 시 결과창에 새 설정 즉시 반영."""
        dialog = SettingsDialog(self._main_window if self._main_window.isVisible() else None)
        if dialog.exec() == SettingsDialog.Accepted:
            # 결과창의 cloud config 캐시 무효화 (다음 OCR 부터 새 설정 사용)
            if hasattr(self._main_window, "reload_cloud_config"):
                self._main_window.reload_cloud_config()

    # ── 1) 전체화면 OCR ─────────────────────────────────────────
    def fullscreen_ocr(self) -> None:
        log.info("fullscreen_ocr triggered")
        # 메인 창이 화면에 찍히지 않도록 잠시 숨김
        self._main_window.hide()
        QTimer.singleShot(180, self._do_fullscreen_capture)

    def _do_fullscreen_capture(self) -> None:
        try:
            image = capture.capture_all_monitors()
            log.info("fullscreen capture: size=%s", image.size)
        except Exception as exc:  # noqa: BLE001
            log.exception("Fullscreen capture failed")
            QMessageBox.critical(None, "캡처 실패", str(exc))
            self._show_main_window()
            return
        self._show_main_window()
        self._main_window.load_new_image(image, mode="fullscreen")

    # ── 2) 구역 OCR ─────────────────────────────────────────────
    def region_ocr(self) -> None:
        if self._overlay is not None:
            return
        self._main_window.hide()
        QTimer.singleShot(150, self._start_region_overlay)

    def _start_region_overlay(self) -> None:
        if self._overlay is not None:
            return
        self._overlay = RegionOverlay()
        self._overlay.selected.connect(self._on_region_selected)
        self._overlay.cancelled.connect(self._on_region_cancelled)
        self._overlay.show_overlay()

    def _on_region_selected(self, rect) -> None:
        self._overlay = None
        QTimer.singleShot(80, lambda: self._capture_region_now(rect))

    def _on_region_cancelled(self) -> None:
        self._overlay = None
        self._show_main_window()

    def _capture_region_now(self, rect) -> None:
        log.info("region_ocr capture: rect=%s", rect)
        try:
            image = capture.capture_region(rect)
            log.info("region capture: size=%s", image.size)
        except Exception as exc:  # noqa: BLE001
            log.exception("Region capture failed (rect=%s)", rect)
            QMessageBox.critical(None, "캡처 실패", str(exc))
            self._show_main_window()
            return
        self._show_main_window()
        self._main_window.load_new_image(image, mode="region")

    # ── 3) 브라우저 풀페이지 OCR ────────────────────────────────
    def browser_ocr(self) -> None:
        dialog = UrlInputDialog(self._main_window if self._main_window.isVisible() else None)
        if dialog.exec() != UrlInputDialog.Accepted:
            return
        url = dialog.url()
        if not url:
            return

        self._browser_progress = QProgressDialog(
            "브라우저로 페이지를 로딩하고 캡처 중…", None, 0, 0,
            self._main_window,
        )
        self._browser_progress.setWindowTitle("Binave OCR")
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
        url = self._browser_worker._url if self._browser_worker else None  # noqa: SLF001
        self._show_main_window()
        self._main_window.load_new_image(image, mode="browser", source_url=url)

    def _on_browser_failed(self, message: str) -> None:
        if self._browser_progress:
            self._browser_progress.close()
            self._browser_progress = None
        QMessageBox.critical(
            self._main_window,
            "브라우저 캡처 실패",
            f"{message}\n\n"
            "Playwright 브라우저가 설치되지 않았다면 다음 명령을 실행하세요:\n"
            "  playwright install chromium",
        )

    # ── 4) 파일에서 OCR ─────────────────────────────────────────
    def file_ocr(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self._main_window,
            "OCR할 파일 선택",
            "",
            file_loader.FILE_DIALOG_FILTER,
        )
        if not path:
            return
        if not file_loader.is_supported(path):
            QMessageBox.warning(
                self._main_window,
                "지원하지 않는 형식",
                "이미지(PNG/JPG/BMP/GIF/TIFF/WebP) 또는 PDF만 지원합니다.",
            )
            return
        try:
            image, page_count = file_loader.load(path)
        except Exception as exc:  # noqa: BLE001
            log.exception("file_loader failed for %s", path)
            QMessageBox.critical(self._main_window, "파일 열기 실패", str(exc))
            return
        if page_count > 1:
            # PDF 다중 페이지: 첫 페이지만 안내
            QMessageBox.information(
                self._main_window,
                "PDF 첫 페이지만 인식",
                f"이 PDF는 {page_count}페이지입니다. 현재는 첫 페이지만 OCR합니다.",
            )
        self._main_window.load_new_image(image, mode="file", source_url=path)

    # ── 진입점 ──────────────────────────────────────────────────
    def run(self) -> int:
        return self._qapp.exec()


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = BinaveOCRApp()
    return app.run()

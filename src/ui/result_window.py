"""OCR 결과 창. 좌측 캡처 이미지, 우측 인식 텍스트.

상단 툴바에 복사 / 저장 / 다시 OCR 버튼을 둠. 윈도우 스니핑 도구처럼
캡처 직후 자동으로 클립보드에도 텍스트를 복사한다.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

log = logging.getLogger(__name__)

from PIL import Image
from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSettings,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import styles as S
from .feedback import BusyOverlay, NewOCRSheet, show_toast

from ..core.easyocr_engine import EasyOCREngine
from ..core.ocr_engine import OCREngine, OCRResult
from ..features import history
from ..features.barcode import Barcode, detect_barcodes
from ..features.cloud_ocr import (
    POLICY_AUTO_FALLBACK,
    POLICY_CLOUD_PREFERRED,
    POLICY_LOCAL_ONLY,
    CloudOCRConfig,
    CloudOCRError,
    make_provider,
)
from ..features.preprocess import auto as auto_preprocess, enhance_for_retry
from ..features.translate import LANG_LABELS, TranslationResult, translate
from ..utils.clipboard import copy_text

_SETTINGS_ORG = "Binave OCR"
_SETTINGS_APP = "Binave OCR"
_KEY_TARGET_LANG = "translate/target_lang"


_PRIMARY_BUTTON_STYLE = """
QPushButton {
    font-size: 16px;
    font-weight: 600;
    color: white;
    background: #007acc;
    border: none;
    border-radius: 8px;
    padding: 0 24px;
}
QPushButton:hover { background: #1389d8; }
QPushButton:pressed { background: #005a9e; }
QPushButton:disabled { background: #9bbcd6; color: #e0e0e0; }
"""

_SECONDARY_BUTTON_STYLE = """
QPushButton {
    font-size: 13px;
    color: #333;
    background: #f5f6f8;
    border: 1px solid #d8dde3;
    border-radius: 6px;
    padding: 0 16px;
}
QPushButton:hover { background: #e8f4ff; border-color: #007acc; }
QPushButton:pressed { background: #d4eaff; }
QPushButton:disabled { color: #a0a0a0; background: #efefef; }
"""

_COMBO_STYLE = """
QComboBox {
    font-size: 13px;
    background: white;
    border: 1px solid #d8dde3;
    border-radius: 6px;
    padding: 0 12px;
    min-width: 120px;
}
QComboBox:hover { border-color: #007acc; }
QComboBox::drop-down { border: none; width: 24px; }
"""

_SEGMENT_STYLE = """
QPushButton {
    background: transparent;
    border: none;
    padding: 7px 4px;
    font-size: 13px;
    font-weight: 500;
    color: rgba(60, 60, 67, 0.6);
}
QPushButton:checked {
    background: white;
    border-radius: 8px;
    font-weight: 600;
    color: #1a1a1a;
}
"""

_SEARCH_STYLE = """
QLineEdit {
    background: rgba(118, 118, 128, 0.12);
    border: none;
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 14px;
    color: #1a1a1a;
}
QLineEdit:focus { background: rgba(118, 118, 128, 0.18); }
"""


class _SegmentedToggle(QWidget):
    """[원본 | 결과] 두 옵션 사이에서 하나만 선택되는 토글 컨트롤."""

    changed = Signal(str)  # 'source' or 'result'

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(S.SEGMENTED_CONTAINER_QSS)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._source_btn = QPushButton("원본", self)
        self._result_btn = QPushButton("결과", self)
        for btn in (self._source_btn, self._result_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(S.SEGMENT_BUTTON_QSS)
            self._group.addButton(btn)
            layout.addWidget(btn)
        # 기본: 결과 선택
        self._result_btn.setChecked(True)
        self._source_btn.toggled.connect(self._on_toggled)
        self._result_btn.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        if not checked:
            return  # 다른 버튼 켜진 시점에서도 호출되지만 한 번만 처리
        self.changed.emit(self.current())

    def current(self) -> str:
        return "source" if self._source_btn.isChecked() else "result"

    def set_current(self, value: str) -> None:
        if value == "source":
            self._source_btn.setChecked(True)
        else:
            self._result_btn.setChecked(True)


class _ImageViewerDialog(QDialog):
    """원본 이미지를 모달로 표시. 창 크기에 맞춰 자동 스케일."""

    def __init__(self, image: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("원본 이미지")
        self.resize(900, 700)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self._label = _FitImageLabel(scroll)
        pixmap = self._pil_to_pixmap(image)
        self._label.setOriginalPixmap(pixmap)
        scroll.setWidget(self._label)
        layout.addWidget(scroll)

        close_btn = QPushButton("닫기", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    @staticmethod
    def _pil_to_pixmap(image: Image.Image) -> QPixmap:
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        return pixmap


class _FitImageLabel(QLabel):
    """패널 크기에 맞춰 비율을 유지하며 자동 스케일되는 이미지 라벨."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap_orig: QPixmap | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    def setOriginalPixmap(self, pixmap: QPixmap) -> None:
        self._pixmap_orig = pixmap
        self._rescale()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap_orig is None or self._pixmap_orig.isNull():
            return
        target = self.size()
        if target.width() <= 1 or target.height() <= 1:
            return
        scaled = self._pixmap_orig.scaled(
            target,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        super().setPixmap(scaled)


class _TranslateWorker(QThread):
    finished_ok = Signal(object)  # TranslationResult
    failed = Signal(str)

    def __init__(self, text: str, target: str, source: str = "auto") -> None:
        super().__init__()
        self._text = text
        self._target = target
        self._source = source

    def run(self) -> None:
        try:
            result = translate(self._text, self._target, self._source)
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            log.exception("translate worker failed")
            self.failed.emit(str(exc))


class _OCRWorker(QThread):
    finished_ok = Signal(object, object, str)  # OCRResult, list[Barcode], engine
    failed = Signal(str)

    def __init__(
        self, image: Image.Image, lang: str = "korean",
        cloud_config: CloudOCRConfig | None = None,
        force_cloud: bool = False,
    ) -> None:
        super().__init__()
        self._image = image
        self._lang = lang
        self._cloud_config = cloud_config or CloudOCRConfig()
        self._force_cloud = force_cloud  # 수동 버튼 시 True — 로컬 스킵하고 클라우드만

    def run(self) -> None:
        try:
            # 수동 클라우드 호출: 로컬 OCR 건너뛰고 클라우드로만 인식
            if self._force_cloud:
                result, engine = self._cloud_only()
                barcodes = detect_barcodes(self._image)
                self.finished_ok.emit(result, barcodes, engine)
                return

            cfg = self._cloud_config

            # CLOUD_PREFERRED + 키 OK: 로컬 건너뛰고 클라우드 first.
            # 클라우드 실패/빈 결과면 로컬로 자연 폴백.
            if cfg.policy == POLICY_CLOUD_PREFERRED and cfg.is_ready():
                try:
                    cloud_result, cloud_engine = self._cloud_only()
                    if cloud_result.lines:
                        log.info("OCR worker: CLOUD_PREFERRED — cloud succeeded, skipping local")
                        barcodes = detect_barcodes(self._image)
                        self.finished_ok.emit(cloud_result, barcodes, cloud_engine)
                        return
                    log.warning("OCR worker: CLOUD_PREFERRED returned empty → local fallback")
                except CloudOCRError as exc:
                    log.warning("OCR worker: CLOUD_PREFERRED failed (%s) → local fallback", exc)

            processed = auto_preprocess(self._image)
            result, engine = self._run_ensemble(processed)
            # 1차 결과가 약하면 향상 전처리 적용 후 재시도, 더 좋은 쪽 채택
            result, engine = self._maybe_retry_enhanced(processed, result, engine)

            # AUTO_FALLBACK 정책일 때만 자동 클라우드 호출.
            # LOCAL_ONLY: 자동 호출 X. CLOUD_PREFERRED: 위에서 이미 시도했으니 스킵.
            if cfg.policy == POLICY_AUTO_FALLBACK:
                result, engine = self._maybe_cloud_fallback(self._image, result, engine)
            # 바코드는 원본 이미지 기준 (전처리로 코드가 깨질 수 있음)
            barcodes = detect_barcodes(self._image)
            self.finished_ok.emit(result, barcodes, engine)
        except Exception as exc:  # noqa: BLE001
            log.exception("OCR worker failed")
            self.failed.emit(str(exc))

    def _maybe_retry_enhanced(
        self, processed: Image.Image, result: OCRResult, engine: str,
    ) -> tuple[OCRResult, str]:
        """1차 결과가 약하면 CLAHE + 언샤프 적용 후 재시도. 더 좋은 쪽 선택.

        트리거 조건 (engine-aware): paddle conf < 0.75 또는 easy conf < 0.50,
        또는 인식 글자 수가 너무 적음 (< 10).
        """
        if not _is_low_quality(result, engine):
            return result, engine

        log.info(
            "OCR worker: low-quality 1st pass (engine=%s, %s) → enhanced retry",
            engine, _summary(result),
        )
        try:
            enhanced = enhance_for_retry(processed)
        except Exception:  # noqa: BLE001
            log.exception("enhance_for_retry failed; keeping original result")
            return result, engine

        try:
            enh_result, enh_engine = self._run_ensemble(enhanced)
        except Exception:  # noqa: BLE001
            log.exception("enhanced ensemble failed; keeping original result")
            return result, engine

        best, best_engine, reason = _pick_better_pass(result, engine, enh_result, enh_engine)
        log.info(
            "OCR worker: retry decision — %s (orig=%s/%s, enh=%s/%s)",
            reason, engine, _summary(result), enh_engine, _summary(enh_result),
        )
        return best, best_engine

    def _maybe_cloud_fallback(
        self, original_image: Image.Image, result: OCRResult, engine: str,
    ) -> tuple[OCRResult, str]:
        """자동 폴백: 로컬 결과가 여전히 약하면 클라우드 호출 후 더 좋은 쪽 채택.

        설정 OFF 또는 키 미설정이면 즉시 패스. 네트워크/API 오류는 로컬 결과 유지.
        """
        cfg = self._cloud_config
        if not cfg.auto_fallback or not cfg.is_ready():
            return result, engine
        if not _is_low_quality(result, engine):
            return result, engine

        provider = make_provider(cfg)
        if provider is None:
            return result, engine

        log.info(
            "OCR worker: low-quality after enhanced retry (engine=%s, %s) → cloud fallback (%s)",
            engine, _summary(result), provider.name,
        )
        try:
            cloud_result = provider.recognize(original_image)
        except CloudOCRError as exc:
            log.warning("Cloud OCR failed (%s): %s — keeping local result", provider.name, exc)
            return result, engine

        cloud_engine = f"cloud:{provider.name}"
        best, best_engine, reason = _pick_better_pass(result, engine, cloud_result, cloud_engine)
        log.info(
            "OCR worker: cloud fallback decision — %s (local=%s/%s, cloud=%s/%s)",
            reason, engine, _summary(result), cloud_engine, _summary(cloud_result),
        )
        return best, best_engine

    def _cloud_only(self) -> tuple[OCRResult, str]:
        """수동 클라우드 인식 — 로컬 건너뛰고 클라우드만 사용."""
        cfg = self._cloud_config
        provider = make_provider(cfg)
        if provider is None:
            log.warning("Cloud-only requested but no provider configured")
            return OCRResult(lines=[]), "cloud:unconfigured"
        log.info("OCR worker: manual cloud-only request (%s)", provider.name)
        try:
            result = provider.recognize(self._image)
            return result, f"cloud:{provider.name}"
        except CloudOCRError as exc:
            log.error("Cloud-only failed (%s): %s", provider.name, exc)
            raise

    def _run_ensemble(self, image: Image.Image) -> tuple[OCRResult, str]:
        """PaddleOCR과 EasyOCR을 병렬로 돌리고 더 좋은 결과 선택. 엔진명도 반환."""
        from concurrent.futures import ThreadPoolExecutor

        def _paddle() -> OCRResult:
            engine = OCREngine.instance(self._lang)
            return engine.recognize(image)

        def _easy() -> OCRResult:
            engine = EasyOCREngine.instance()
            if engine is None:
                return OCRResult(lines=[])
            return engine.recognize(image)

        paddle_result: OCRResult | None = None
        easy_result: OCRResult | None = None
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(_paddle): "paddle", pool.submit(_easy): "easy"}
            for fut in futures:
                name = futures[fut]
                try:
                    if name == "paddle":
                        paddle_result = fut.result()
                    else:
                        easy_result = fut.result()
                except Exception:  # noqa: BLE001
                    log.exception("%s engine failed in ensemble", name)

        chosen, engine, reason = _pick_best_result(paddle_result, easy_result)
        log.info("ensemble winner: %s — %s (paddle=%s easy=%s)",
                 engine, reason,
                 _summary(paddle_result),
                 _summary(easy_result))
        return chosen, engine


def _pick_best_result(
    paddle: OCRResult | None,
    easy: OCRResult | None,
) -> tuple[OCRResult, str, str]:
    """두 엔진 결과 중 더 좋은 쪽 선택.

    두 엔진의 confidence는 척도가 달라 직접 비교가 부적절.
    실측: 더 많은 글자를 인식한 쪽이 일반적으로 더 정확함 (둘 다 over-segmentation 없는 가정).
    1차: 비공백 글자 수 차이가 ±10% 초과면 더 많은 쪽.
    2차: 글자 수 비슷하면 같은 엔진의 avg_conf로 결정 (어차피 둘 중 하나 차이가 적은 경우).
    """
    p_ok = paddle is not None and paddle.lines
    e_ok = easy is not None and easy.lines

    if p_ok and e_ok:
        p_chars = _char_count(paddle)
        e_chars = _char_count(easy)
        denom = max(p_chars, e_chars, 1)
        diff = (e_chars - p_chars) / denom

        if abs(diff) > 0.10:
            if e_chars > p_chars:
                return easy, "easy", f"chars={e_chars} > paddle={p_chars}"
            return paddle, "paddle", f"chars={p_chars} > easy={e_chars}"

        p_avg = _avg_conf(paddle)
        e_avg = _avg_conf(easy)
        if p_avg >= e_avg:
            return paddle, "paddle", f"chars≈, p_conf={p_avg:.2f}≥e_conf={e_avg:.2f}"
        return easy, "easy", f"chars≈, e_conf={e_avg:.2f}>p_conf={p_avg:.2f}"

    if p_ok:
        return paddle, "paddle", "easy empty"
    if e_ok:
        return easy, "easy", "paddle empty"
    return OCRResult(lines=[]), "none", "both empty"


def _avg_conf(result: OCRResult | None) -> float:
    if result is None or not result.lines:
        return 0.0
    return sum(l.confidence for l in result.lines) / len(result.lines)


def _is_low_quality(result: OCRResult | None, engine: str) -> bool:
    """엔진별 임계값으로 OCR 결과의 약함 여부 판정 (재시도 트리거).

    PaddleOCR 와 EasyOCR 의 conf 척도가 다르므로 engine-aware:
      paddle: avg < 0.75
      easy:   avg < 0.50
    또는 글자 수 < 10 (어떤 엔진이든 너무 적음).
    """
    if result is None or not result.lines:
        return True
    if _char_count(result) < 10:
        return True
    avg = _avg_conf(result)
    if engine == "paddle" and avg < 0.75:
        return True
    if engine == "easy" and avg < 0.50:
        return True
    return False


def _pick_better_pass(
    a: OCRResult, a_engine: str,
    b: OCRResult, b_engine: str,
) -> tuple[OCRResult, str, str]:
    """원본 vs 향상-전처리 두 OCR pass 결과 비교.

    글자 수 ±10% 초과 시 더 많은 쪽. 비슷할 때는 같은 엔진끼리만 conf 비교 (이종 비교 금지).
    이종 엔진 + 글자 수 비슷이면 보수적으로 a (원본) 유지.
    """
    a_chars = _char_count(a)
    b_chars = _char_count(b)
    if a_chars == 0 and b_chars == 0:
        return a, a_engine, "both empty, keep original"
    if a_chars == 0:
        return b, b_engine, "original empty"
    if b_chars == 0:
        return a, a_engine, "enhanced empty"

    denom = max(a_chars, b_chars, 1)
    diff = (b_chars - a_chars) / denom
    if abs(diff) > 0.10:
        if b_chars > a_chars:
            return b, b_engine, f"enhanced chars {b_chars} > {a_chars}"
        return a, a_engine, f"original chars {a_chars} > {b_chars}"

    if a_engine == b_engine:
        a_avg = _avg_conf(a)
        b_avg = _avg_conf(b)
        if b_avg > a_avg + 0.02:
            return b, b_engine, f"chars≈, same engine conf {b_avg:.2f}>{a_avg:.2f}"
        return a, a_engine, f"chars≈, same engine conf {a_avg:.2f}≥{b_avg:.2f}"
    return a, a_engine, "chars≈, cross-engine — keep original (safer)"


def _char_count(result: OCRResult | None) -> int:
    if result is None:
        return 0
    return sum(len(line.text.strip()) for line in result.lines)


def _summary(result: OCRResult | None) -> str:
    if result is None:
        return "n/a"
    if not result.lines:
        return "0 lines"
    return f"{len(result.lines)} lines avg_conf={_avg_conf(result):.3f}"


class ResultWindow(QMainWindow):
    new_ocr_requested = Signal()                # 시트 표시 요청 (호환)
    fullscreen_ocr_requested = Signal()         # 시트에서 전체화면 선택
    region_ocr_requested = Signal()             # 시트에서 구역 선택
    browser_ocr_requested = Signal()            # 시트에서 웹페이지 선택
    file_ocr_requested = Signal()               # 시트에서 파일에서 선택

    def __init__(
        self,
        image: Image.Image | None = None,
        *,
        lang: str = "korean",
        mode: str = "unknown",
        source_url: str | None = None,
    ) -> None:
        super().__init__()
        self._image: Image.Image | None = image
        self._lang = lang
        self._mode = mode
        self._source_url = source_url
        self._worker: _OCRWorker | None = None
        self._translate_worker: _TranslateWorker | None = None
        self._current_history_id: int | None = None
        self._last_engine: str = ""
        self._last_avg_conf: float = 0.0
        self._last_lines: list = []  # OCRLine 리스트 — source view 디텍션 박스용
        self._busy_overlay: BusyOverlay | None = None
        self._new_ocr_sheet: NewOCRSheet | None = None

        # 클라우드 OCR 설정 캐시 (다이얼로그에서 변경 시 reload_cloud_config() 호출)
        from .settings_dialog import load_cloud_config
        self._cloud_config: CloudOCRConfig = load_cloud_config()

        self.setWindowTitle("Binave OCR — 결과")
        self.resize(1180, 720)
        self._build_ui()
        self._refresh_history()

        if image is not None:
            self._start_ocr()
        else:
            # 브라우즈 모드: OCR 없이 히스토리만 보여주는 시작.
            self._set_idle_placeholder()

    def _build_ui(self) -> None:
        # ── 본문 컨테이너 (헤더 + 분할 영역) ──────────────────────────────
        # 핸드오프 스펙: 루트 캔버스에 그라데이션 → 자식 패널들이 반투명으로 비침
        central = QWidget(self)
        central.setObjectName("rootCanvas")
        central.setStyleSheet(S.ROOT_CANVAS_QSS)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 1) 상단 헤더 — 프로그램 이름만
        outer.addWidget(self._build_top_header())

        # 2) 본문: 좌측 사이드바 + 우측 패널(인라인 툴바 + 스택)
        splitter = QSplitter(Qt.Horizontal, central)
        splitter.addWidget(self._build_left_pane())

        right_panel = QWidget(splitter)
        right_panel.setStyleSheet(S.DETAIL_CONTAINER_QSS)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 10, 12, 12)
        right_layout.setSpacing(10)

        # 인라인 툴바 (우측 패널 상단 고정 — 토글 무관)
        right_layout.addWidget(self._build_inline_toolbar(right_panel))

        # 결과/원본 스택
        self._detail_stack = QStackedWidget(right_panel)
        self._result_view = self._build_text_panel()   # index 0
        self._source_view = self._build_source_view()  # index 1
        self._detail_stack.addWidget(self._result_view)
        self._detail_stack.addWidget(self._source_view)
        self._detail_stack.setCurrentIndex(0)
        right_layout.addWidget(self._detail_stack, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([270, 910])
        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        outer.addWidget(splitter, stretch=1)

        self.setCentralWidget(central)

        # 상태바 + 진행 바
        self._status = QStatusBar(self)
        self._progress = QProgressBar(self)
        self._progress.setMaximumWidth(180)
        self._progress.setRange(0, 0)
        self._progress.hide()
        self._status.addPermanentWidget(self._progress)
        self.setStatusBar(self._status)

    def _build_top_header(self) -> QWidget:
        header = QFrame(self)
        header.setObjectName("topHeader")
        header.setFixedHeight(40)
        header.setStyleSheet(S.TOP_HEADER_QSS)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(0)
        title = QLabel("Binave OCR", header)
        title.setObjectName("appTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        # 우측 끝: 설정 톱니 버튼 (트레이 메뉴가 숨겨져 있어 발견 어려움 → 헤더에서 직접 접근)
        self._settings_btn = QPushButton("⚙", header)
        self._settings_btn.setObjectName("headerSettingsBtn")
        self._settings_btn.setFlat(True)
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setToolTip("설정")
        self._settings_btn.setStyleSheet(
            f"QPushButton#headerSettingsBtn {{ "
            f"  border: none; background: transparent; "
            f"  color: {S.LABEL_SECONDARY}; font-size: 18px; border-radius: 8px; "
            f"}} "
            f"QPushButton#headerSettingsBtn:hover {{ background: {S.FILL_QUATERNARY}; color: {S.LABEL}; }} "
            f"QPushButton#headerSettingsBtn:pressed {{ background: {S.FILL_TERTIARY}; }}"
        )
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)
        return header

    def _open_settings(self) -> None:
        """헤더 톱니 버튼: 설정 다이얼로그 오픈. 저장 시 cloud config 즉시 반영."""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec() == SettingsDialog.Accepted:
            self.reload_cloud_config()

    def _build_inline_toolbar(self, parent: QWidget) -> QWidget:
        """우측 패널 상단에 들어가는 인라인 툴바 (토글 변경 무관 고정)."""
        bar = QFrame(parent)
        bar.setObjectName("inlineToolbar")
        bar.setStyleSheet(S.INLINE_TOOLBAR_QSS)
        # 살짝 떠 있는 느낌의 그림자
        shadow = QGraphicsDropShadowEffect(bar)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 30))
        bar.setGraphicsEffect(shadow)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # 보조 액션
        self._copy_btn = self._make_secondary_button("복사", self._copy_text)
        self._save_text_btn = self._make_secondary_button("저장", self._save_text)
        self._save_image_btn = self._make_secondary_button("이미지", self._save_image)
        self._retry_btn = self._make_secondary_button("다시 OCR", self._start_ocr)
        self._cloud_btn = self._make_secondary_button("☁ 클라우드 인식", self._start_cloud_ocr)
        for btn in (self._copy_btn, self._save_text_btn, self._save_image_btn,
                    self._retry_btn, self._cloud_btn):
            layout.addWidget(btn)

        # 자동 OCR 정책 콤보 — 클라우드 인식 버튼 옆 (즉시 전환)
        self._policy_combo = QComboBox(bar)
        self._policy_combo.setMinimumHeight(34)
        self._policy_combo.setStyleSheet(S.COMBO_QSS)
        self._policy_combo.addItem("로컬만", POLICY_LOCAL_ONLY)
        self._policy_combo.addItem("자동 폴백", POLICY_AUTO_FALLBACK)
        self._policy_combo.addItem("클라우드 우선", POLICY_CLOUD_PREFERRED)
        self._policy_combo.setToolTip(
            "자동 OCR 동작 정책\n"
            "• 로컬만: 클라우드 자동 호출 X (수동 버튼만)\n"
            "• 자동 폴백: 로컬 결과 약할 때만 클라우드 (비용 ↓)\n"
            "• 클라우드 우선: 키 있으면 무조건 클라우드 (속도/품질 ↑)"
        )
        self._policy_combo.currentIndexChanged.connect(self._on_policy_combo_changed)
        layout.addWidget(self._policy_combo)

        # 초기 정책/클라우드 버튼 상태 동기화 (콤보 시그널 연결 후 호출 — 시그널은 무시됨)
        self._sync_policy_combo_from_config()
        self._update_cloud_button_state()

        # 구분선
        sep = QFrame(bar)
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {S.SEPARATOR_LIGHT}; margin: 6px 4px;")
        layout.addWidget(sep)

        # 번역 + 언어 콤보
        self._translate_btn = self._make_secondary_button("번역", self._on_translate)
        self._lang_combo = QComboBox(bar)
        self._lang_combo.setMinimumHeight(34)
        self._lang_combo.setStyleSheet(S.COMBO_QSS)
        for code, label in LANG_LABELS.items():
            self._lang_combo.addItem(label, code)
        saved_lang = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(_KEY_TARGET_LANG, "ko")
        idx = self._lang_combo.findData(saved_lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        layout.addWidget(self._translate_btn)
        layout.addWidget(self._lang_combo)

        # spacer
        spacer = QWidget(bar)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(spacer)

        # CTA + 새 OCR
        self._new_ocr_btn = QPushButton("+ 새 OCR", bar)
        self._new_ocr_btn.setToolTip("새 OCR 시작")
        self._new_ocr_btn.setMinimumSize(120, 36)
        self._new_ocr_btn.setCursor(Qt.PointingHandCursor)
        self._new_ocr_btn.setStyleSheet(S.PRIMARY_BUTTON_QSS)
        self._new_ocr_btn.clicked.connect(self._show_new_ocr_sheet)
        cta_shadow = QGraphicsDropShadowEffect(self._new_ocr_btn)
        cta_shadow.setBlurRadius(18)
        cta_shadow.setOffset(0, 4)
        cta_shadow.setColor(QColor(0, 122, 255, 110))
        self._new_ocr_btn.setGraphicsEffect(cta_shadow)
        self._cta_pulse = QPropertyAnimation(cta_shadow, b"blurRadius", self)
        self._cta_pulse.setDuration(2600)
        self._cta_pulse.setStartValue(14.0)
        self._cta_pulse.setKeyValueAt(0.5, 28.0)
        self._cta_pulse.setEndValue(14.0)
        self._cta_pulse.setEasingCurve(QEasingCurve.InOutSine)
        self._cta_pulse.setLoopCount(-1)
        self._cta_pulse.start()
        layout.addWidget(self._new_ocr_btn)
        return bar

    def _build_source_view(self) -> QWidget:
        panel = QWidget(self)
        panel.setStyleSheet(S.DETAIL_CONTAINER_QSS)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        # 헤더: 라벨 + 줌 컨트롤
        header = QHBoxLayout()
        src_label = QLabel("원본 캡처", panel)
        src_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {S.LABEL_SECONDARY}; "
            "letter-spacing: 0.06em; padding: 4px;"
        )
        header.addWidget(src_label)
        header.addStretch(1)

        zoom_box = QFrame(panel)
        zoom_box.setStyleSheet(S.ZOOM_BOX_QSS)
        zoom_layout = QHBoxLayout(zoom_box)
        zoom_layout.setContentsMargins(3, 3, 3, 3)
        zoom_layout.setSpacing(0)
        self._zoom_minus = QPushButton("−", zoom_box)
        self._zoom_minus.setFixedSize(28, 24)
        self._zoom_minus.setCursor(Qt.PointingHandCursor)
        self._zoom_minus.setStyleSheet(S.ZOOM_BUTTON_QSS)
        self._zoom_minus.clicked.connect(lambda: self._on_zoom_change(-10))
        self._zoom_label = QLabel("100%", zoom_box)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        self._zoom_label.setMinimumWidth(40)
        self._zoom_label.setStyleSheet(S.ZOOM_LABEL_QSS)
        self._zoom_plus = QPushButton("+", zoom_box)
        self._zoom_plus.setFixedSize(28, 24)
        self._zoom_plus.setCursor(Qt.PointingHandCursor)
        self._zoom_plus.setStyleSheet(S.ZOOM_BUTTON_QSS)
        self._zoom_plus.clicked.connect(lambda: self._on_zoom_change(10))
        zoom_layout.addWidget(self._zoom_minus)
        zoom_layout.addWidget(self._zoom_label)
        zoom_layout.addWidget(self._zoom_plus)
        header.addWidget(zoom_box)
        layout.addLayout(header)

        # 캔버스: 스크롤 영역 안에 이미지 라벨
        scroll = QScrollArea(panel)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; border-radius: 16px; }")
        scroll.viewport().setStyleSheet("background: #f5f5f7;")

        self._source_image_label = _FitImageLabel(scroll)
        self._source_image_label.setMinimumSize(200, 200)
        scroll.setWidget(self._source_image_label)
        layout.addWidget(scroll, stretch=1)

        # 푸터 정보바
        self._source_info_label = QLabel("이미지 없음", panel)
        self._source_info_label.setStyleSheet(S.INFO_FOOTER_QSS)
        layout.addWidget(self._source_info_label)

        self._zoom_value = 100
        return panel

    def _make_secondary_button(self, text: str, slot) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setMinimumHeight(36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(S.SECONDARY_BUTTON_QSS)
        btn.clicked.connect(slot)
        return btn

    def _build_left_pane(self) -> QWidget:
        panel = QWidget(self)
        panel.setStyleSheet(S.SIDEBAR_QSS)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 8, 12)
        layout.setSpacing(10)

        # 1) 타이틀
        title = QLabel("Binave OCR", panel)
        title.setStyleSheet(
            f"font-weight: 600; font-size: 22px; color: {S.LABEL}; padding: 4px 6px;"
        )
        layout.addWidget(title)

        # 2) 세그먼티드 토글 [원본 | 결과]
        self._toggle = _SegmentedToggle(panel)
        self._toggle.changed.connect(self._on_view_changed)
        layout.addWidget(self._toggle)

        # 3) 검색바
        self._search_input = QLineEdit(panel)
        self._search_input.setPlaceholderText("검색")
        self._search_input.setStyleSheet(S.SEARCH_QSS)
        self._search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_input)

        # 4) 섹션 헤더
        section = QHBoxLayout()
        sec_label = QLabel("최근 OCR", panel)
        sec_label.setStyleSheet(
            f"font-size: 11px; font-weight: 500; color: {S.LABEL_SECONDARY}; "
            "letter-spacing: 0.06em; padding: 2px 10px 4px;"
        )
        section.addWidget(sec_label)
        section.addStretch(1)
        clear_btn = QPushButton("모두 삭제", panel)
        clear_btn.setStyleSheet(
            f"QPushButton {{ font-size: 11px; color: {S.LABEL_SECONDARY}; "
            "background: transparent; border: none; padding: 4px 6px; } "
            f"QPushButton:hover {{ color: {S.SYS_RED}; }}"
        )
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._on_history_clear_all)
        section.addWidget(clear_btn)
        layout.addLayout(section)

        # 5) 히스토리 리스트
        self._history_list = QListWidget(panel)
        self._history_list.setStyleSheet(S.HISTORY_LIST_QSS)
        self._history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_list.customContextMenuRequested.connect(self._on_history_context_menu)
        self._history_list.itemActivated.connect(self._on_history_item_activated)
        self._history_list.itemClicked.connect(self._on_history_item_activated)
        layout.addWidget(self._history_list)
        return panel

    def _build_text_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setStyleSheet(S.DETAIL_CONTAINER_QSS)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        # 바코드 섹션 (감지된 코드가 있을 때만 표시)
        self._barcode_label = QLabel("QR / 바코드", panel)
        self._barcode_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {S.TINT}; "
            "letter-spacing: 0.06em; padding: 4px 4px 0;"
        )
        self._barcode_text = QPlainTextEdit(panel)
        self._barcode_text.setReadOnly(True)
        self._barcode_text.setMaximumHeight(110)
        self._barcode_text.setStyleSheet(S.PANEL_CARD_QSS)
        self._barcode_label.hide()
        self._barcode_text.hide()
        layout.addWidget(self._barcode_label)
        layout.addWidget(self._barcode_text)

        # OCR 결과 카드
        ocr_label = QLabel("OCR 결과", panel)
        ocr_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {S.LABEL_SECONDARY}; "
            "letter-spacing: 0.06em; padding: 4px 4px 0;"
        )
        layout.addWidget(ocr_label)

        self._text = QPlainTextEdit(panel)
        self._text.setPlaceholderText("OCR 결과가 여기에 표시됩니다…")
        self._text.setStyleSheet(S.PANEL_CARD_QSS)
        layout.addWidget(self._text, stretch=1)

        # 번역 결과 — 처음엔 숨김, 사용자가 번역 버튼 누르면 표시.
        # 헤더: 좌측 라벨 + 우측 [복사] 버튼 (번역 결과만 클립보드로).
        self._translate_label = QLabel("번역", panel)
        self._translate_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {S.TINT}; "
            "letter-spacing: 0.06em; padding: 4px 4px 0;"
        )
        self._translate_copy_btn = QPushButton("복사", panel)
        self._translate_copy_btn.setMinimumHeight(30)
        self._translate_copy_btn.setMinimumWidth(64)
        self._translate_copy_btn.setCursor(Qt.PointingHandCursor)
        self._translate_copy_btn.setStyleSheet(S.TINTED_BUTTON_QSS)
        self._translate_copy_btn.clicked.connect(self._copy_translation)

        translate_header_layout = QHBoxLayout()
        translate_header_layout.setContentsMargins(0, 0, 0, 0)
        translate_header_layout.setSpacing(8)
        translate_header_layout.addWidget(self._translate_label)
        translate_header_layout.addStretch(1)
        translate_header_layout.addWidget(self._translate_copy_btn)

        self._translate_header = QWidget(panel)
        self._translate_header.setLayout(translate_header_layout)

        self._translate_text = QPlainTextEdit(panel)
        self._translate_text.setReadOnly(True)
        self._translate_text.setPlaceholderText("번역 결과가 여기에 표시됩니다…")
        self._translate_text.setStyleSheet(S.PANEL_CARD_QSS)

        # OCR 결과 ↔ 번역 결과 사이 구분선 (둘 다 흰 카드라 시각 분리 어려움)
        self._translate_separator = QFrame(panel)
        self._translate_separator.setFrameShape(QFrame.HLine)
        self._translate_separator.setFixedHeight(1)
        self._translate_separator.setStyleSheet(
            f"background: {S.SEPARATOR}; border: none; margin: 4px 8px;"
        )

        self._translate_header.hide()
        self._translate_text.hide()
        self._translate_separator.hide()
        layout.addWidget(self._translate_separator)
        layout.addWidget(self._translate_header)
        layout.addWidget(self._translate_text, stretch=1)

        return panel

    # ── OCR 실행 ─────────────────────────────────────────────────
    def _start_ocr(self) -> None:
        if self._image is None:
            QMessageBox.information(self, "OCR", "OCR할 이미지가 없습니다. [+ 새 OCR]로 캡처하세요.")
            return
        if self._worker and self._worker.isRunning():
            return
        self._set_busy(True, "OCR 인식 중…")
        self._text.setPlainText("")
        self._show_busy_overlay("인식 중…")
        self._worker = _OCRWorker(self._image, self._lang, cloud_config=self._cloud_config)
        self._worker.finished_ok.connect(self._on_ocr_ok)
        self._worker.failed.connect(self._on_ocr_failed)
        self._worker.start()

    def _start_cloud_ocr(self) -> None:
        """수동 클라우드 인식 — 로컬 결과와 무관하게 클라우드만 호출."""
        if self._image is None:
            QMessageBox.information(self, "OCR", "OCR할 이미지가 없습니다.")
            return
        if not self._cloud_config.is_ready():
            QMessageBox.information(
                self, "클라우드 OCR 설정 필요",
                "트레이 메뉴 → '설정…'에서 클라우드 OCR 활성화 + API 키 입력이 필요합니다.",
            )
            return
        if self._worker and self._worker.isRunning():
            return
        self._set_busy(True, "클라우드 OCR…")
        self._show_busy_overlay("클라우드 인식 중…")
        self._worker = _OCRWorker(
            self._image, self._lang,
            cloud_config=self._cloud_config, force_cloud=True,
        )
        self._worker.finished_ok.connect(self._on_ocr_ok)
        self._worker.failed.connect(self._on_ocr_failed)
        self._worker.start()

    def reload_cloud_config(self) -> None:
        """설정 다이얼로그에서 저장 후 호출. 다음 OCR 부터 새 설정 적용."""
        from .settings_dialog import load_cloud_config
        self._cloud_config = load_cloud_config()
        self._sync_policy_combo_from_config()
        self._update_cloud_button_state()
        log.info(
            "ResultWindow: cloud config reloaded (enabled=%s, policy=%s, ready=%s)",
            self._cloud_config.enabled, self._cloud_config.policy,
            self._cloud_config.is_ready(),
        )

    def _sync_policy_combo_from_config(self) -> None:
        """현재 self._cloud_config.policy 와 콤보 선택을 일치시킴.
        시그널 일시 차단으로 _on_policy_combo_changed 재진입 방지.
        """
        if not hasattr(self, "_policy_combo"):
            return
        idx = self._policy_combo.findData(self._cloud_config.policy)
        if idx < 0:
            return
        self._policy_combo.blockSignals(True)
        try:
            self._policy_combo.setCurrentIndex(idx)
        finally:
            self._policy_combo.blockSignals(False)

    def _on_policy_combo_changed(self) -> None:
        """툴바 콤보에서 정책 변경 시 즉시 QSettings 에 저장 + 캐시 갱신."""
        new_policy = self._policy_combo.currentData()
        if not new_policy:
            return
        from .settings_dialog import save_policy_only
        save_policy_only(str(new_policy))
        # 캐시 갱신 (frozen dataclass 라서 새 인스턴스 만들기)
        self._cloud_config = CloudOCRConfig(
            enabled=self._cloud_config.enabled,
            provider=self._cloud_config.provider,
            google_api_key=self._cloud_config.google_api_key,
            policy=str(new_policy),
        )
        log.info("Cloud OCR policy changed (toolbar): %s", new_policy)

    def _update_cloud_button_state(self) -> None:
        """클라우드 버튼 활성화/툴팁을 현재 설정 기준으로 갱신."""
        if not hasattr(self, "_cloud_btn"):
            return
        ready = self._cloud_config.is_ready()
        self._cloud_btn.setEnabled(ready)
        if ready:
            self._cloud_btn.setToolTip(
                f"클라우드 OCR ({self._cloud_config.provider})로 다시 인식 — "
                "로컬 결과를 덮어씀"
            )
        else:
            self._cloud_btn.setToolTip(
                "트레이 → '설정…'에서 클라우드 OCR 활성화 + API 키 입력 필요"
            )

    def _show_busy_overlay(self, label: str) -> None:
        if self._busy_overlay is not None:
            return
        central = self.centralWidget()
        if central is None:
            return
        overlay = BusyOverlay(central, label)
        overlay.show_at_parent()
        self._busy_overlay = overlay

    def _hide_busy_overlay(self) -> None:
        if self._busy_overlay is not None:
            self._busy_overlay.hide_overlay()
            self._busy_overlay = None

    def _on_ocr_ok(self, result: OCRResult, barcodes: list[Barcode], engine: str) -> None:
        self._hide_busy_overlay()
        msg = f"인식 완료 — {len(result.lines)} 줄 ({engine})"
        if barcodes:
            msg += f" / 바코드 {len(barcodes)}건"
        self._set_busy(False, msg)
        self._text.setPlainText(result.text)
        self._render_barcodes(barcodes)
        self._last_engine = engine
        self._last_avg_conf = (
            sum(l.confidence for l in result.lines) / len(result.lines)
            if result.lines else 0.0
        )
        self._last_lines = list(result.lines)
        # 히스토리 저장 (히스토리에서 불러온 항목이면 중복 저장 회피)
        try:
            self._current_history_id = history.add_entry(
                text=result.text,
                image=self._image,
                mode=self._mode,
                source_url=self._source_url,
                avg_confidence=self._last_avg_conf,
                engine=engine,
            )
            self._refresh_history()
        except Exception:  # noqa: BLE001
            log.exception("history: failed to add entry on OCR complete")

        # 새로 OCR 했으니 원본 뷰도 함께 갱신
        self._refresh_source_view()
        if result.text:
            copy_text(result.text)
            self._status.showMessage("결과를 클립보드에 복사했습니다.", 4000)

    # ── 새 OCR 시트 ──────────────────────────────────────────────
    def _show_new_ocr_sheet(self) -> None:
        # 중앙 위젯 위에 오버레이로 띄움
        central = self.centralWidget()
        if central is None:
            self.new_ocr_requested.emit()
            return
        if self._new_ocr_sheet is not None:
            return
        sheet = NewOCRSheet(central)
        sheet.fullscreen_chosen.connect(self.fullscreen_ocr_requested.emit)
        sheet.region_chosen.connect(self.region_ocr_requested.emit)
        sheet.browser_chosen.connect(self.browser_ocr_requested.emit)
        sheet.file_chosen.connect(self.file_ocr_requested.emit)
        sheet.cancelled.connect(lambda: setattr(self, "_new_ocr_sheet", None))
        for sig in (
            sheet.fullscreen_chosen, sheet.region_chosen,
            sheet.browser_chosen, sheet.file_chosen,
        ):
            sig.connect(lambda: setattr(self, "_new_ocr_sheet", None))
        sheet.show_at_parent()
        self._new_ocr_sheet = sheet

    # ── 새 이미지 로딩 (싱글 윈도우 모드용) ─────────────────────
    def load_new_image(
        self,
        image: Image.Image,
        *,
        mode: str = "unknown",
        source_url: str | None = None,
    ) -> None:
        """기존 창을 재활용해 새 이미지로 OCR 시작."""
        self._image = image
        self._mode = mode
        self._source_url = source_url
        self._current_history_id = None
        self._last_lines = []
        self._last_engine = ""
        self._last_avg_conf = 0.0

        # 결과 뷰로 자동 전환
        self._toggle.set_current("result")

        # 패널 초기화
        self._text.setPlainText("")
        self._set_translation_visible(False)
        self._translate_text.setPlainText("")
        self._render_barcodes([])

        # OCR 시작
        self._start_ocr()

    # 창 [X] = 종료가 아니라 트레이로 숨김
    def closeEvent(self, event):  # noqa: N802
        event.ignore()
        self.hide()

    # ── 토글/검색/소스 뷰 ────────────────────────────────────────
    def _on_view_changed(self, view: str) -> None:
        idx = 1 if view == "source" else 0
        self._detail_stack.setCurrentIndex(idx)
        if view == "source":
            self._refresh_source_view()

    def _refresh_source_view(self) -> None:
        if self._image is None:
            self._source_image_label.clear()
            self._source_info_label.setText("이미지 없음")
            return
        pixmap = _pil_to_pixmap(self._image)
        self._source_image_label.setOriginalPixmap(pixmap)
        base_w, base_h = self._image.size
        scaled_w = int(base_w * self._zoom_value / 100)
        scaled_h = int(base_h * self._zoom_value / 100)
        self._source_image_label.setMinimumSize(scaled_w, scaled_h)
        # 정보바
        info_parts = [f"{base_w} × {base_h}"]
        if self._last_lines:
            info_parts.append(f"{len(self._last_lines)}개 영역")
        if self._last_engine:
            info_parts.append(f"엔진: {self._last_engine}")
        if self._last_avg_conf:
            info_parts.append(f"평균 신뢰도 {self._last_avg_conf*100:.0f}%")
        self._source_info_label.setText(" · ".join(info_parts))

    def _on_zoom_change(self, delta: int) -> None:
        self._zoom_value = max(50, min(200, self._zoom_value + delta))
        self._zoom_label.setText(f"{self._zoom_value}%")
        self._refresh_source_view()

    def _on_search_changed(self, text: str) -> None:
        text_lower = text.strip().lower()
        for i in range(self._history_list.count()):
            item = self._history_list.item(i)
            if not text_lower:
                item.setHidden(False)
                continue
            haystack = item.text().lower()
            tooltip = (item.toolTip() or "").lower()
            item.setHidden(text_lower not in haystack and text_lower not in tooltip)

    # ── 히스토리 ─────────────────────────────────────────────────
    def _refresh_history(self) -> None:
        """DB에서 다시 불러와 리스트 갱신."""
        self._history_list.clear()
        for entry in history.list_recent(limit=200):
            item = QListWidgetItem(self._history_list)
            item.setData(Qt.UserRole, entry.id)
            display = self._format_history_label(entry)
            item.setText(display)
            item.setToolTip(entry.text[:300])
            self._history_list.addItem(item)

    @staticmethod
    def _format_history_label(entry: history.HistoryEntry) -> str:
        # ISO -> 사람이 읽기 좋은 형식 (간단 변환)
        ts = entry.created_at.replace("T", " ")[:16]
        preview = " ".join(entry.text.split())[:60]
        if len(preview) >= 60:
            preview += "…"
        mode_label = {
            "fullscreen": "전체화면",
            "region": "구역",
            "browser": "웹페이지",
            "file": "파일",
        }.get(entry.mode, entry.mode)
        return f"[{mode_label}] {ts}\n{preview}"

    def _on_history_item_activated(self, item: QListWidgetItem) -> None:
        entry_id = item.data(Qt.UserRole)
        if entry_id is None:
            return
        entry = history.get_entry(int(entry_id))
        if entry is None:
            return
        self._load_entry(entry)

    def _load_entry(self, entry: history.HistoryEntry) -> None:
        self._current_history_id = entry.id
        self._mode = entry.mode
        self._source_url = entry.source_url
        self._last_engine = entry.engine
        self._last_avg_conf = entry.avg_confidence
        # 히스토리 항목엔 박스 정보가 없으므로 비움 (재OCR 하면 다시 채워짐)
        self._last_lines = []
        self._text.setPlainText(entry.text)
        # 이미지는 디스크에서 로드 (있으면)
        if entry.image_path:
            try:
                self._image = Image.open(entry.image_path).convert("RGB")
            except Exception:  # noqa: BLE001
                log.exception("history: failed to load image %s", entry.image_path)
                self._image = None
        else:
            self._image = None
        # 번역
        if entry.translation_target and entry.translation_text:
            self._translate_label.setText(
                f"번역 → {LANG_LABELS.get(entry.translation_target, entry.translation_target)}"
            )
            self._translate_text.setPlainText(entry.translation_text)
            self._set_translation_visible(True)
            self._translate_copy_btn.setEnabled(bool(entry.translation_text.strip()))
        else:
            self._set_translation_visible(False)
            self._translate_text.setPlainText("")
        # 바코드/진행바 정리
        self._render_barcodes([])
        self._set_busy(False, f"히스토리 항목 #{entry.id} 불러옴")
        self._refresh_source_view()

    def _on_history_context_menu(self, pos) -> None:
        item = self._history_list.itemAt(pos)
        if item is None:
            return
        entry_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        delete_act = menu.addAction("삭제")
        chosen = menu.exec(self._history_list.mapToGlobal(pos))
        if chosen == delete_act and entry_id is not None:
            history.delete_entry(int(entry_id))
            if self._current_history_id == entry_id:
                self._current_history_id = None
            self._refresh_history()

    def _on_history_clear_all(self) -> None:
        confirm = QMessageBox.question(
            self,
            "히스토리 모두 삭제",
            "정말 모든 히스토리 항목과 캡처 이미지를 삭제할까요?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        history.clear_all()
        self._current_history_id = None
        self._refresh_history()

    def _set_idle_placeholder(self) -> None:
        """브라우즈 모드(이미지 없음): 우측 패널을 비워두고 안내."""
        self._text.setPlainText("")
        self._text.setPlaceholderText(
            "히스토리 항목을 클릭해서 불러오거나, [+ 새 OCR] 로 새 인식을 시작하세요."
        )
        self._refresh_source_view()
        self._set_busy(False, "히스토리 보기")

    # ── 번역 ─────────────────────────────────────────────────────
    def _on_translate(self) -> None:
        text = self._text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "번역", "번역할 텍스트가 없습니다.")
            return
        target = self._lang_combo.currentData()
        if not target:
            return
        # 마지막 선택 언어 저장
        QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(_KEY_TARGET_LANG, target)

        if self._translate_worker and self._translate_worker.isRunning():
            return

        label_text = f"번역 → {LANG_LABELS.get(target, target)}"
        self._translate_label.setText(label_text)
        self._translate_text.setPlainText("번역 중…")
        self._set_translation_visible(True)
        self._translate_copy_btn.setEnabled(False)  # 결과 도착 후 활성화
        self._translate_btn.setEnabled(False)
        self._translate_btn.setText("번역 중…")

        self._translate_worker = _TranslateWorker(text, target)
        self._translate_worker.finished_ok.connect(self._on_translate_ok)
        self._translate_worker.failed.connect(self._on_translate_failed)
        self._translate_worker.start()

    def _on_translate_ok(self, result: TranslationResult) -> None:
        self._translate_btn.setEnabled(True)
        self._translate_btn.setText("번역")
        if result.text:
            self._translate_text.setPlainText(result.text)
            self._translate_copy_btn.setEnabled(True)
            self._status.showMessage(
                f"번역 완료 ({result.engine}, {LANG_LABELS.get(result.target_lang, result.target_lang)})",
                4000,
            )
            # 현재 히스토리 항목이 있으면 번역 결과 갱신
            if self._current_history_id:
                try:
                    history.update_translation(
                        self._current_history_id, result.target_lang, result.text
                    )
                    self._refresh_history()
                except Exception:  # noqa: BLE001
                    log.exception("history: translation update failed")
        else:
            self._translate_text.setPlainText("(번역 결과 없음)")
            self._translate_copy_btn.setEnabled(False)

    def _on_translate_failed(self, message: str) -> None:
        self._translate_btn.setEnabled(True)
        self._translate_btn.setText("번역")
        self._translate_text.setPlainText("")
        self._translate_copy_btn.setEnabled(False)
        QMessageBox.warning(self, "번역 실패", f"번역 중 오류:\n{message}")

    def _set_translation_visible(self, visible: bool) -> None:
        """번역 헤더 + 텍스트 박스 + 위 구분선을 함께 보이거나 숨김."""
        self._translate_separator.setVisible(visible)
        self._translate_header.setVisible(visible)
        self._translate_text.setVisible(visible)

    def _copy_translation(self) -> None:
        text = self._translate_text.toPlainText().strip()
        if not text or text in ("번역 중…", "(번역 결과 없음)"):
            return
        copy_text(text)
        show_toast(self, "번역 결과가 클립보드에 복사됨")

    def _render_barcodes(self, barcodes: list[Barcode]) -> None:
        if not barcodes:
            self._barcode_label.hide()
            self._barcode_text.hide()
            self._barcode_text.setPlainText("")
            return
        lines = [f"[{b.type}] {b.data}" for b in barcodes]
        self._barcode_text.setPlainText("\n".join(lines))
        self._barcode_label.show()
        self._barcode_text.show()

    def _on_ocr_failed(self, message: str) -> None:
        self._hide_busy_overlay()
        self._set_busy(False, "OCR 실패")
        QMessageBox.critical(self, "OCR 실패", message)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._progress.setVisible(busy)
        for btn in (
            self._copy_btn,
            self._save_text_btn,
            self._retry_btn,
        ):
            btn.setEnabled(not busy)
        if message:
            self._status.showMessage(message)

    # ── actions ──────────────────────────────────────────────────
    def _copy_text(self) -> None:
        text = self._text.toPlainText()
        if text:
            copy_text(text)
            show_toast(self, "텍스트가 클립보드에 복사됨")

    def _save_text(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self, "텍스트 저장", "ocr_result.txt", "Text (*.txt)"
        )
        if not path_str:
            return
        Path(path_str).write_text(self._text.toPlainText(), encoding="utf-8")
        show_toast(self, "텍스트 저장 완료")

    def _save_image(self) -> None:
        if self._image is None:
            QMessageBox.information(self, "이미지 저장", "저장할 원본 이미지가 없습니다.")
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self, "이미지 저장", "capture.png", "PNG (*.png)"
        )
        if not path_str:
            return
        self._image.save(path_str, format="PNG")
        show_toast(self, "이미지 저장 완료")

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _pil_to_pixmap(image: Image.Image) -> QPixmap:
        return _pil_to_pixmap(image)


def _pil_to_pixmap(image: Image.Image) -> QPixmap:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap

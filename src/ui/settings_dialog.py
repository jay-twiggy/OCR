"""클라우드 OCR 설정 다이얼로그.

QSettings 에 영구 저장. 트레이 메뉴 → "설정…" 으로 진입.
키 형식: cloud/* 그룹.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from . import styles as S
from ..features.cloud_ocr import (
    POLICY_AUTO_FALLBACK,
    VALID_POLICIES,
    CloudOCRConfig,
)

log = logging.getLogger(__name__)

_SETTINGS_ORG = "Binave OCR"
_SETTINGS_APP = "Binave OCR"

# QSettings 키 (cloud/* 그룹)
KEY_CLOUD_ENABLED = "cloud/enabled"
KEY_CLOUD_PROVIDER = "cloud/provider"
KEY_CLOUD_GOOGLE_API_KEY = "cloud/google_api_key"
KEY_CLOUD_POLICY = "cloud/policy"


def load_cloud_config() -> CloudOCRConfig:
    """현재 저장된 설정을 읽어와 CloudOCRConfig 로 반환.

    policy 기본값은 AUTO_FALLBACK (안전한 비용 통제).
    잘못된/구버전 값이면 기본값으로 폴백.
    """
    s = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    policy = str(s.value(KEY_CLOUD_POLICY, POLICY_AUTO_FALLBACK))
    if policy not in VALID_POLICIES:
        policy = POLICY_AUTO_FALLBACK
    return CloudOCRConfig(
        enabled=s.value(KEY_CLOUD_ENABLED, False, type=bool),
        provider=str(s.value(KEY_CLOUD_PROVIDER, "google_vision")),
        google_api_key=str(s.value(KEY_CLOUD_GOOGLE_API_KEY, "")),
        policy=policy,
    )


def save_cloud_config(cfg: CloudOCRConfig) -> None:
    s = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.setValue(KEY_CLOUD_ENABLED, cfg.enabled)
    s.setValue(KEY_CLOUD_PROVIDER, cfg.provider)
    s.setValue(KEY_CLOUD_GOOGLE_API_KEY, cfg.google_api_key)
    s.setValue(KEY_CLOUD_POLICY, cfg.policy)
    s.sync()


def save_policy_only(policy: str) -> None:
    """툴바 콤보에서 정책만 단독 변경 시 사용 (다이얼로그 안 거치고 즉시 저장)."""
    if policy not in VALID_POLICIES:
        return
    s = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.setValue(KEY_CLOUD_POLICY, policy)
    s.sync()


class SettingsDialog(QDialog):
    """클라우드 OCR 설정 다이얼로그.

    UI 그룹: 활성화 토글, 프로바이더 선택, API 키 입력, 자동 폴백 토글.
    자동 폴백 첫 활성화 시 비용/개인정보 주의 다이얼로그 표시.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Binave OCR — 설정")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog {{ background: {S.SURFACE_PANEL}; }}")

        self._cfg = load_cloud_config()
        self._build_ui()
        self._populate_from_config()
        self._wire_signals()

    # ── UI 구축 ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("클라우드 OCR")
        title_font = QFont(self.font())
        title_font.setPointSize(14)
        title_font.setWeight(QFont.DemiBold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {S.LABEL};")
        root.addWidget(title)

        desc = QLabel(
            "로컬 OCR 정확도가 부족할 때 Google Cloud Vision 으로 보강합니다. "
            "본인 API 키를 사용하므로 비용·개인정보는 사용자가 통제합니다."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {S.LABEL_SECONDARY}; font-size: 12px;")
        root.addWidget(desc)

        # 활성화 토글
        self._enabled_chk = QCheckBox("클라우드 OCR 활성화")
        self._enabled_chk.setStyleSheet(f"color: {S.LABEL};")
        root.addWidget(self._enabled_chk)

        # 폼
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._provider_cb = QComboBox()
        self._provider_cb.addItem("Google Vision", "google_vision")
        form.addRow("프로바이더", self._provider_cb)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("AIzaSy... (Google Cloud 콘솔에서 발급)")
        form.addRow("API 키", self._api_key_edit)

        root.addLayout(form)

        info = QLabel(
            "💡 자동 OCR 동작(로컬만/자동 폴백/클라우드 우선)은 결과창 툴바의 "
            "정책 콤보에서 즉시 전환할 수 있습니다.\n"
            "ℹ️ 무료 1,000장/월 초과 시 본인 Google Cloud 계정으로 비용 발생."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {S.LABEL_SECONDARY}; font-size: 11px;")
        root.addWidget(info)

        # ── API 키 발급 가이드 (펼침 가능) ─────────────────────────────
        guide = QLabel(
            "<b>API 키 발급 방법 (Google Cloud)</b><br>"
            "1. <a href='https://console.cloud.google.com/' style='color:#007AFF;'>Google Cloud 콘솔</a> 접속 → 프로젝트 만들기/선택<br>"
            "2. <a href='https://console.cloud.google.com/apis/library/vision.googleapis.com' style='color:#007AFF;'>Vision API 라이브러리</a>에서 <b>'사용 설정'</b> 클릭<br>"
            "3. <a href='https://console.cloud.google.com/apis/credentials' style='color:#007AFF;'>사용자 인증 정보</a> → <b>'+ 사용자 인증 정보 만들기' → 'API 키'</b><br>"
            "4. 생성된 키(<code>AIzaSy…</code>)를 복사해서 위 'API 키' 칸에 붙여넣기<br>"
            "<span style='color:rgba(0,0,0,0.5);'>(권장) 키 제한 → API 제한 → Cloud Vision API 만 허용</span>"
        )
        guide.setWordWrap(True)
        guide.setOpenExternalLinks(True)
        guide.setTextInteractionFlags(Qt.TextBrowserInteraction)
        guide.setStyleSheet(
            f"QLabel {{ color: {S.LABEL}; font-size: 11px; "
            f"background: {S.FILL_QUATERNARY}; border-radius: 8px; padding: 10px 12px; }}"
        )
        root.addWidget(guide)

        # 버튼
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText("저장")
        buttons.button(QDialogButtonBox.Cancel).setText("취소")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── 데이터 채우기 ─────────────────────────────────────────────────
    def _populate_from_config(self) -> None:
        self._enabled_chk.setChecked(self._cfg.enabled)

        idx = self._provider_cb.findData(self._cfg.provider)
        if idx >= 0:
            self._provider_cb.setCurrentIndex(idx)

        self._api_key_edit.setText(self._cfg.google_api_key)

        self._update_enabled_state()

    def _wire_signals(self) -> None:
        self._enabled_chk.toggled.connect(self._update_enabled_state)

    def _update_enabled_state(self) -> None:
        """활성화 토글 OFF 시 하위 입력 비활성화."""
        on = self._enabled_chk.isChecked()
        self._provider_cb.setEnabled(on)
        self._api_key_edit.setEnabled(on)

    # ── 저장 ─────────────────────────────────────────────────────────
    def _on_accept(self) -> None:
        # policy 는 다이얼로그에서 안 다룸 — 기존 값 유지 (툴바 콤보가 변경)
        new_cfg = CloudOCRConfig(
            enabled=self._enabled_chk.isChecked(),
            provider=str(self._provider_cb.currentData() or "google_vision"),
            google_api_key=self._api_key_edit.text().strip(),
            policy=self._cfg.policy,
        )

        # 활성화했지만 키 없음 → 경고
        if new_cfg.enabled and not new_cfg.google_api_key:
            QMessageBox.warning(
                self, "API 키 필요",
                "클라우드 OCR 활성화하려면 API 키를 입력해야 합니다.",
            )
            self._api_key_edit.setFocus()
            return

        save_cloud_config(new_cfg)
        self._cfg = new_cfg
        log.info(
            "Cloud OCR settings saved: enabled=%s provider=%s policy=%s key_set=%s",
            new_cfg.enabled, new_cfg.provider, new_cfg.policy,
            bool(new_cfg.google_api_key),
        )
        self.accept()

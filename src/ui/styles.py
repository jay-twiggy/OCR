"""SnipOCR 디자인 토큰 (iOS 26 스타일).

iOS / iPadOS 디자인 시스템의 색·타입·간격·재료 토큰을 한 곳에서 관리.
다크모드는 지원하지 않는다 (라이트 단일).
"""
from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


# ── Color tokens ──────────────────────────────────────────────────────────────

# System tints
TINT = "#007AFF"                  # 기본 강조색 (iOS Blue)
TINT_HOVER = "#1389d8"
TINT_PRESSED = "#005a9e"
TINT_DARK = "#0050a0"             # 그라데이션 하단

SYS_RED = "#FF3B30"
SYS_GREEN = "#34C759"
SYS_ORANGE = "#FF9500"

# Labels (translucent black)
LABEL = "rgba(0, 0, 0, 0.85)"
LABEL_SECONDARY = "rgba(60, 60, 67, 0.6)"
LABEL_TERTIARY = "rgba(60, 60, 67, 0.3)"
PLACEHOLDER = "rgba(60, 60, 67, 0.3)"

# Backgrounds
WALLPAPER_GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e8eef7, stop:0.5 #f3e8ee, stop:1 #fef3e6)"
SURFACE_LIGHT = "rgba(255, 255, 255, 0.55)"
SURFACE_PANEL = "rgba(255, 255, 255, 0.85)"
SURFACE_SIDEBAR = "rgba(242, 242, 247, 0.92)"
SURFACE_GLASS = "rgba(255, 255, 255, 0.72)"

# Fills
FILL_QUATERNARY = "rgba(120, 120, 128, 0.10)"
FILL_TERTIARY = "rgba(118, 118, 128, 0.12)"
FILL_SECONDARY = "rgba(118, 118, 128, 0.16)"
FILL_PRIMARY = "rgba(118, 118, 128, 0.18)"

# Separator
SEPARATOR = "rgba(60, 60, 67, 0.29)"
SEPARATOR_LIGHT = "rgba(60, 60, 67, 0.10)"

# Borders for glass
GLASS_INNER_STROKE = "rgba(255, 255, 255, 0.6)"


# ── Typography ────────────────────────────────────────────────────────────────

def apply_app_font(app: QApplication) -> None:
    """앱 전역 기본 폰트 설정. 시스템 폰트 폴백 체인."""
    font = QFont()
    # 우선순위: Apple SD Gothic Neo (Mac 한글) → Segoe UI (Win) → Malgun Gothic (Win 한글)
    # PySide6는 setFamilies로 폴백 체인을 받음
    font.setFamilies([
        "-apple-system",
        "SF Pro Display",
        "SF Pro Text",
        "Segoe UI",
        "Apple SD Gothic Neo",
        "Malgun Gothic",
        "맑은 고딕",
        "Helvetica Neue",
        "Arial",
        "sans-serif",
    ])
    font.setPointSize(10)
    app.setFont(font)
    # 전역 iOS 스타일 스크롤바
    existing = app.styleSheet() or ""
    app.setStyleSheet(existing + "\n" + IOS_SCROLLBAR_QSS)


# ── Common stylesheets ────────────────────────────────────────────────────────

PRIMARY_BUTTON_QSS = f"""
QPushButton {{
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {TINT}, stop:1 {TINT_DARK});
    border: none;
    border-radius: 12px;
    padding: 0 18px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.24px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {TINT_HOVER}, stop:1 {TINT});
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {TINT_PRESSED}, stop:1 {TINT_DARK});
}}
QPushButton:disabled {{
    background: #9bbcd6;
    color: #e0e0e0;
}}
"""

SECONDARY_BUTTON_QSS = f"""
QPushButton {{
    color: {LABEL};
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 0 12px;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: -0.24px;
}}
QPushButton:hover {{ background: {FILL_QUATERNARY}; }}
QPushButton:pressed {{ background: {FILL_TERTIARY}; }}
QPushButton:disabled {{ color: {LABEL_TERTIARY}; }}
"""

# 언어 풀다운 / 일반 콤보
COMBO_QSS = f"""
QComboBox {{
    background: {FILL_TERTIARY};
    border: none;
    border-radius: 10px;
    padding: 0 12px;
    font-size: 14px;
    font-weight: 500;
    color: {LABEL};
    min-width: 110px;
}}
QComboBox:hover {{ background: {FILL_SECONDARY}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: white;
    border: 1px solid {SEPARATOR_LIGHT};
    border-radius: 10px;
    padding: 4px;
    selection-background-color: rgba(0, 122, 255, 0.14);
    selection-color: {LABEL};
}}
"""

# 세그먼티드 토글 컨테이너
SEGMENTED_CONTAINER_QSS = f"background: {FILL_PRIMARY}; border-radius: 10px;"

# 세그먼티드 토글 안의 각 버튼
SEGMENT_BUTTON_QSS = f"""
QPushButton {{
    background: transparent;
    border: none;
    padding: 7px 4px;
    font-size: 13px;
    font-weight: 500;
    color: {LABEL_SECONDARY};
}}
QPushButton:checked {{
    background: white;
    border-radius: 8px;
    font-weight: 600;
    color: {LABEL};
}}
"""

SEARCH_QSS = f"""
QLineEdit {{
    background: {FILL_TERTIARY};
    border: none;
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 14px;
    color: {LABEL};
}}
QLineEdit:focus {{ background: {FILL_SECONDARY}; }}
"""

# 좌측 사이드바 컨테이너
SIDEBAR_QSS = f"QWidget {{ background: {SURFACE_SIDEBAR}; }}"

# 좌측 히스토리 리스트
HISTORY_LIST_QSS = f"""
QListWidget {{
    border: none;
    background: transparent;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 8px;
    margin-bottom: 2px;
    color: {LABEL};
}}
QListWidget::item:selected {{
    background: rgba(0, 122, 255, 0.14);
    color: #003a66;
}}
QListWidget::item:hover:!selected {{
    background: {FILL_QUATERNARY};
}}
"""

# 결과/번역 패널 카드
PANEL_CARD_QSS = f"""
QPlainTextEdit {{
    background: {SURFACE_PANEL};
    border: none;
    border-radius: 16px;
    padding: 14px 18px;
    font-size: 15px;
    color: {LABEL};
}}
QPlainTextEdit:focus {{
    background: rgba(255, 255, 255, 0.95);
}}
"""

# 우측 디테일 컨테이너
DETAIL_CONTAINER_QSS = f"QWidget {{ background: {SURFACE_LIGHT}; }}"

# 플로팅 글라스 툴바 (메인윈도우 QToolBar 스타일)
FLOATING_TOOLBAR_QSS = f"""
QToolBar {{
    background: {SURFACE_GLASS};
    border: 1px solid {GLASS_INNER_STROKE};
    border-radius: 14px;
    padding: 6px;
    spacing: 4px;
    margin: 8px 12px 4px 12px;
}}
QToolBar::separator {{
    background: {SEPARATOR_LIGHT};
    width: 1px;
    margin: 6px 4px;
}}
"""

# 줌 컨트롤 박스
ZOOM_BOX_QSS = f"""
QFrame {{
    background: {FILL_TERTIARY};
    border: none;
    border-radius: 8px;
}}
"""

ZOOM_BUTTON_QSS = f"""
QPushButton {{
    background: transparent;
    border: none;
    color: {TINT};
    font-size: 16px;
    font-weight: 600;
}}
QPushButton:hover {{ color: {TINT_HOVER}; }}
"""

ZOOM_LABEL_QSS = f"""
QLabel {{
    font-size: 12px;
    font-weight: 500;
    color: {LABEL_SECONDARY};
}}
"""

# 정보 푸터 바
INFO_FOOTER_QSS = f"""
QLabel {{
    font-size: 13px;
    font-weight: 500;
    color: {LABEL_SECONDARY};
    background: {SURFACE_PANEL};
    border: 1px solid {SEPARATOR_LIGHT};
    border-radius: 12px;
    padding: 10px 14px;
}}
"""

# 상단 헤더 (프로그램 이름 표시)
TOP_HEADER_QSS = f"""
QFrame#topHeader {{
    background: {SURFACE_GLASS};
    border: none;
    border-bottom: 1px solid {SEPARATOR_LIGHT};
}}
QFrame#topHeader QLabel#appTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {LABEL};
    letter-spacing: -0.2px;
}}
"""

# 우측 패널 안의 도구 툴바 (인라인)
INLINE_TOOLBAR_QSS = f"""
QFrame#inlineToolbar {{
    background: {SURFACE_GLASS};
    border: 1px solid {GLASS_INNER_STROKE};
    border-radius: 14px;
    padding: 6px;
}}
"""

# iOS 스타일 스크롤바 (전역)
IOS_SCROLLBAR_QSS = """
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
    border: none;
}
QScrollBar::handle:vertical {
    background: rgba(60, 60, 67, 0.28);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(60, 60, 67, 0.5);
}
QScrollBar::handle:vertical:pressed {
    background: rgba(60, 60, 67, 0.65);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0; background: transparent; border: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: rgba(60, 60, 67, 0.28);
    border-radius: 3px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(60, 60, 67, 0.5);
}
QScrollBar::handle:horizontal:pressed {
    background: rgba(60, 60, 67, 0.65);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0; background: transparent; border: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""

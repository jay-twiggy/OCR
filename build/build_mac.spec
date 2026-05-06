# -*- mode: python ; coding: utf-8 -*-
"""Binave OCR — macOS PyInstaller spec.

빌드 (CI 또는 로컬 Mac):
    pyinstaller build/build_mac.spec --clean --noconfirm

산출물:
    dist/Binave OCR.app + (선택) dist/BinaveOCR-{version}.dmg

전제 조건 (CI에서 자동, 로컬은 수동):
    1. PaddleOCR/EasyOCR 모델 사전 다운로드
       → ~/.paddlex/  &  ~/.EasyOCR/  존재
    2. playwright install chromium
       → ~/Library/Caches/ms-playwright/chromium-*  존재
    3. pip install -r requirements-build.txt

CI workflow (.github/workflows/build-mac.yml) 가
scripts/prepare_models.py 로 1번을 자동 처리함.
"""
import pathlib
import sys

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# ── 빌드 환경 사전 검증 ──────────────────────────────────────────
HOME = pathlib.Path.home()
PADDLEX_DIR = HOME / ".paddlex"
EASYOCR_DIR = HOME / ".EasyOCR"

_missing = [
    (label, p) for label, p in [
        ("PaddleOCR 모델 (.paddlex)", PADDLEX_DIR),
        ("EasyOCR 모델 (.EasyOCR)", EASYOCR_DIR),
    ] if not p.exists()
]
if _missing:
    msg = "\n".join(f"  - {lbl}: {p}" for lbl, p in _missing)
    raise SystemExit(
        f"[Binave OCR build] 다음 캐시를 찾을 수 없습니다:\n{msg}\n\n"
        "scripts/prepare_models.py 를 먼저 실행하세요."
    )


# ── 데이터 (모델 + 라이브러리 리소스) ────────────────────────────
# 주의: macOS 에선 Playwright Chromium 을 번들에 포함하지 않는다.
# 이유: Chrome.app 내부의 .framework 중첩 구조가 PyInstaller 의 ad-hoc 코드사인
# (`--all-architectures` 하드코딩) 과 충돌해 빌드 실패함
# ("bundle format unrecognized" / "subcomponent: ... Framework.framework").
# 사용자는 첫 웹페이지 OCR 사용 시 'playwright install chromium' 1회 실행.
# 메인 기능 (스크린샷/구역/파일 OCR) 은 영향 없음.

datas = [
    (str(PADDLEX_DIR), '_bundled/.paddlex'),
    (str(EASYOCR_DIR), '_bundled/.EasyOCR'),
]

for pkg in (
    'paddle', 'paddleocr', 'paddlex',
    'easyocr',
    'deep_translator',
    'pymupdf',
    'shapely',
    'cv2',
):
    try:
        datas += collect_data_files(pkg, include_py_files=False)
    except Exception as exc:
        print(f"[spec] WARN: collect_data_files({pkg}) failed: {exc}", file=sys.stderr)

# ── 동적 라이브러리 (.dylib/.so) ─────────────────────────────────
binaries = []
for pkg in ('paddle', 'torch', 'torchvision', 'cv2'):
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception as exc:
        print(f"[spec] WARN: collect_dynamic_libs({pkg}) failed: {exc}", file=sys.stderr)

# ── 동적 import 모듈 ────────────────────────────────────────────
hiddenimports = [
    'cv2',
    'mss',
    'pynput',
    'pynput.keyboard._darwin',  # macOS keyboard backend
    'pynput.mouse._darwin',     # macOS mouse backend
    'pyperclip',
    'PIL._tkinter_finder',
    'PIL.Image',
]
for pkg in (
    'paddle', 'paddleocr', 'paddlex',
    'easyocr',
    'deep_translator',
    'pymupdf',
):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception as exc:
        print(f"[spec] WARN: collect_submodules({pkg}) failed: {exc}", file=sys.stderr)

# ── 경로 ────────────────────────────────────────────────────────
SPEC_DIR = pathlib.Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parent

# ── Analysis ────────────────────────────────────────────────────
a = Analysis(
    [str(PROJECT_ROOT / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(SPEC_DIR / 'rthook_set_paths.py')],
    excludes=[
        # 산출물 크기 절감용 — 명백히 미사용인 대형 모듈만 제외
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'jupyterlab',
        'notebook',
        'pytest',
        'sphinx',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BinaveOCR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # paddlepaddle 호환성 — 압축 비활성
    console=False,       # GUI 모드
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,    # 러너 아키텍처 따름 (macos-latest = arm64)
    codesign_identity=None,   # CI workflow 에서 별도 codesign 호출
    entitlements_file=None,
    icon=None,           # TODO: assets/icon.icns 준비 후 경로 지정
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BinaveOCR',
)

# ── macOS .app 번들 ─────────────────────────────────────────────
# Finder 에서 더블클릭 가능한 표준 macOS 앱 형태로 패키징.
app = BUNDLE(
    coll,
    name='Binave OCR.app',
    icon=None,  # TODO: assets/icon.icns
    bundle_identifier='com.binave.ocr',
    info_plist={
        'CFBundleName': 'Binave OCR',
        'CFBundleDisplayName': 'Binave OCR',
        'CFBundleVersion': '0.2.0',
        'CFBundleShortVersionString': '0.2.0',
        'CFBundleIdentifier': 'com.binave.ocr',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        # 사용자 권한 동의 사유 (시스템 다이얼로그에 표시됨)
        'NSScreenCaptureDescription': '스크린샷 OCR 인식을 위해 화면 녹화 권한이 필요합니다.',
        'NSAppleEventsUsageDescription': '글로벌 단축키와 기타 기능을 위해 필요합니다.',
        # Sandboxing 비활성화 (Developer ID 배포에선 OK, App Store 배포 시 필요)
        'LSUIElement': False,
    },
)

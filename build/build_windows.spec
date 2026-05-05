# -*- mode: python ; coding: utf-8 -*-
"""Binave OCR — Windows PyInstaller spec.

빌드:
    pyinstaller build/build_windows.spec --clean --noconfirm

산출물:
    dist/BinaveOCR/BinaveOCR.exe + 동봉 폴더 (예상 ~700MB-1.2GB)

전제 조건 (빌드 직전 확인):
    1. python main.py 를 한 번 실행해 PaddleOCR/EasyOCR 모델 자동 다운로드 완료
       → ~/.paddlex/official_models/  &  ~/.EasyOCR/model/  존재
    2. playwright install chromium 완료
       → ~/AppData/Local/ms-playwright/chromium-*  존재
    3. pip install -r requirements-build.txt
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
PLAYWRIGHT_DIR = HOME / "AppData" / "Local" / "ms-playwright"

_missing = [
    (label, p) for label, p in [
        ("PaddleOCR 모델 (.paddlex)", PADDLEX_DIR),
        ("EasyOCR 모델 (.EasyOCR)", EASYOCR_DIR),
        ("Playwright Chromium", PLAYWRIGHT_DIR),
    ] if not p.exists()
]
if _missing:
    msg = "\n".join(f"  - {lbl}: {p}" for lbl, p in _missing)
    raise SystemExit(
        f"[Binave OCR build] 다음 캐시를 찾을 수 없습니다:\n{msg}\n\n"
        "먼저 'python main.py' 를 한 번 실행해 모델을 다운받거나, "
        "'playwright install chromium' 을 실행하세요."
    )

# ── 데이터 (모델 + 브라우저 + 라이브러리 리소스) ─────────────────
# _bundled/ 아래 모아 두고 런타임 훅에서 사용자 홈으로 시드 / 환경변수 지정
datas = [
    (str(PADDLEX_DIR), '_bundled/.paddlex'),
    (str(EASYOCR_DIR), '_bundled/.EasyOCR'),
    (str(PLAYWRIGHT_DIR), '_bundled/ms-playwright'),
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

# ── 동적 라이브러리 (.dll/.pyd) ──────────────────────────────────
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
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
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
    upx=False,           # paddlepaddle .dll 호환성 — UPX 압축 비활성
    console=False,       # GUI 모드 (콘솔 창 안 뜸)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # TODO: assets/icon.ico 준비 후 경로 지정
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

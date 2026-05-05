"""Binave OCR PyInstaller 런타임 훅.

PyInstaller frozen 환경에서 번들된 OCR 모델 + Playwright Chromium 위치를
사용자 홈으로 시드하거나 환경변수로 가리킨다.

이 훅은 main.py 의 어떤 import 보다도 먼저 실행되므로,
PaddleOCR/EasyOCR/Playwright 가 첫 호출 시 올바른 경로를 본다.
"""
import os
import shutil
import sys
from pathlib import Path


def _seed_dir(src: Path, dst: Path) -> None:
    """src 폴더가 있고 dst 가 없으면 dst 로 복사 (사용자별 첫 실행 1회)."""
    if not src.exists() or dst.exists():
        return
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    except Exception as exc:  # noqa: BLE001
        # 시드 실패해도 앱은 돌게 함 (라이브러리가 자동 다운로드로 폴백)
        print(
            f"[Binave OCR] Failed to seed {src.name} -> {dst}: {exc}",
            file=sys.stderr,
        )


def _setup_bundled_paths() -> None:
    if not getattr(sys, "frozen", False):
        return  # dev 환경 - skip

    # PyInstaller --onedir : sys._MEIPASS = 동봉 폴더 (= dist/BinaveOCR)
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    bundled = bundle_dir / "_bundled"
    if not bundled.exists():
        return

    home = Path.home()

    # ── PaddleOCR 모델 캐시 (~/.paddlex) ───────────────
    # PaddleX 는 모델 위치를 ~/.paddlex 에서 찾으며 환경변수 인식이 일관되지 않음
    # → 사용자 홈에 없으면 번들에서 복사 (~수십 MB, 일회성)
    _seed_dir(bundled / ".paddlex", home / ".paddlex")

    # ── EasyOCR 모델 (~/.EasyOCR) ──────────────────────
    # easyocr Reader 는 model_storage_directory 인자를 받지만,
    # 인자 없이 호출하면 ~/.EasyOCR/model 을 본다 → 시드
    _seed_dir(bundled / ".EasyOCR", home / ".EasyOCR")

    # ── Playwright Chromium ────────────────────────────
    # PLAYWRIGHT_BROWSERS_PATH 환경변수로 번들 위치 직접 지정.
    # (Chromium 자체가 ~250MB → 사용자 홈으로 복사하는 건 비효율, 환경변수가 정석)
    pw_dir = bundled / "ms-playwright"
    if pw_dir.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(pw_dir)


_setup_bundled_paths()

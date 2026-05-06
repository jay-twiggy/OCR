"""CI 빌드용: PaddleOCR + EasyOCR 한국어 모델 사전 다운로드.

PyInstaller 가 빌드 시점에 ~/.paddlex 와 ~/.EasyOCR 를 번들에 포함시키므로,
이 스크립트로 빌드 직전에 모델 캐시를 미리 채워둬야 한다.

용법:
    python scripts/prepare_models.py

성공 시 종료 코드 0, 실패 시 0이 아닌 코드.
GitHub Actions 워크플로우의 빌드 단계 직전에 실행됨.
"""
from __future__ import annotations

import os
import sys

# main.py 와 동일하게 PaddlePaddle OneDNN 회피 환경변수
os.environ.setdefault("FLAGS_use_mkldnn", "false")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "false")


def prepare_paddleocr() -> None:
    print("→ Loading PaddleOCR (Korean) — downloads models on first call…", flush=True)
    from paddleocr import PaddleOCR

    # ocr_engine.py 의 _construct_paddle 와 동일한 인자 (3.x 우선)
    try:
        ocr = PaddleOCR(
            use_textline_orientation=True,
            enable_mkldnn=False,
            lang="korean",
        )
    except TypeError:
        # 더 오래된 버전 폴백
        ocr = PaddleOCR(use_angle_cls=True, lang="korean")
    print(f"  OK — PaddleOCR ready: {type(ocr).__name__}", flush=True)


def prepare_easyocr() -> None:
    print("→ Loading EasyOCR (ko + en) — downloads models on first call…", flush=True)
    import easyocr
    reader = easyocr.Reader(["ko", "en"], gpu=False)
    print(f"  OK — EasyOCR ready: {type(reader).__name__}", flush=True)


def main() -> int:
    try:
        prepare_paddleocr()
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL — PaddleOCR: {exc}", file=sys.stderr, flush=True)
        return 2

    try:
        prepare_easyocr()
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL — EasyOCR: {exc}", file=sys.stderr, flush=True)
        return 3

    # 캐시 위치 표시 (디버깅 도움)
    from pathlib import Path
    home = Path.home()
    for label, path in (
        ("PaddleOCR", home / ".paddlex"),
        ("EasyOCR",   home / ".EasyOCR"),
    ):
        if path.exists():
            print(f"  {label} cache: {path} (exists)", flush=True)
        else:
            print(f"  WARN — {label} cache not found at {path}", flush=True)

    print("✓ Models ready for bundling.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

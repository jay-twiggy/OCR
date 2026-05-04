"""SnipOCR 로깅 설정.

로그는 `<repo>/logs/snipocr.log` 파일과 stderr에 동시에 기록한다.
하나의 파일은 1MB까지 보관하고 5개까지 로테이션.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_INITIALIZED = False


def init_logging(level: int = logging.INFO) -> Path:
    """루트 로거를 설정하고 로그 파일 경로를 반환한다."""
    global _INITIALIZED

    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "snipocr.log"

    if _INITIALIZED:
        return log_path

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    _INITIALIZED = True
    logging.getLogger(__name__).info("Logging initialized → %s", log_path)
    return log_path


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

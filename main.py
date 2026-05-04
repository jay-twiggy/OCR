"""SnipOCR 실행 진입점."""
from __future__ import annotations

import logging
import os
import sys
import traceback

# paddlepaddle 3.x의 OneDNN/PIR 백엔드 호환 이슈 우회 (Windows)
# 참고: ConvertPirAttribute2RuntimeAttribute not support 에러
os.environ.setdefault("FLAGS_use_mkldnn", "false")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "false")

from src.utils.logger import init_logging


def main() -> int:
    log_path = init_logging()
    log = logging.getLogger("snipocr.main")
    log.info("=" * 60)
    log.info("SnipOCR starting (log file: %s)", log_path)

    def _excepthook(exc_type, exc, tb):
        log.error("Uncaught exception:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = _excepthook

    from src.app import main as app_main
    return app_main()


if __name__ == "__main__":
    sys.exit(main())

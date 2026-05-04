"""파일에서 OCR — 이미지/PDF 로더.

이미지: PIL.Image.open
PDF: pymupdf로 첫 페이지 렌더링 (다중 페이지는 추후 확장)
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

FILE_DIALOG_FILTER = (
    "지원 파일 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.pdf);;"
    "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;"
    "PDF (*.pdf);;"
    "모든 파일 (*.*)"
)


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load(path: str | Path, *, pdf_dpi: int = 200) -> tuple[Image.Image, int]:
    """경로에서 이미지를 로드. PDF는 첫 페이지만.

    Returns:
        (PIL.Image RGB, page_count) — page_count는 PDF만 의미. 이미지는 1.
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        img = Image.open(p).convert("RGB")
        log.info("file_loader: image loaded path=%s size=%s", p.name, img.size)
        return img, 1
    if ext in PDF_EXTENSIONS:
        return _load_pdf_first_page(p, dpi=pdf_dpi)
    raise ValueError(f"Unsupported file type: {ext}")


def _load_pdf_first_page(path: Path, dpi: int = 200) -> tuple[Image.Image, int]:
    """PDF 첫 페이지를 PIL.Image로 렌더링."""
    import pymupdf  # 지연 임포트

    doc = pymupdf.open(str(path))
    try:
        if doc.page_count == 0:
            raise ValueError("Empty PDF")
        page_count = doc.page_count
        page = doc[0]
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        log.info(
            "file_loader: PDF first page rendered path=%s size=%s pages=%d",
            path.name, img.size, page_count,
        )
        return img, page_count
    finally:
        doc.close()

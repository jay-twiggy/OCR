"""Playwright 기반 브라우저 풀페이지 캡처.

Option A: 우리 앱이 Chromium을 띄우고 사용자가 입력한 URL을 로딩한 뒤
전체 페이지를 한 번에 캡처한다. 로그인 세션은 재사용하지 않음.

Lazy-load 대응: 페이지를 끝까지 스크롤한 뒤 위로 복귀하여 모든 이미지가
로드되도록 한 후 full_page 캡처를 수행한다.
"""
from __future__ import annotations

import io
import time

from PIL import Image


def capture_full_page(
    url: str,
    *,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    timeout_ms: int = 30000,
    pre_scroll: bool = True,
) -> Image.Image:
    """주어진 URL의 풀페이지 스크린샷을 PIL.Image로 반환.

    Playwright가 설치되어 있어야 하고, `playwright install chromium`이 미리 실행되어 있어야 한다.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="networkidle")

            if pre_scroll:
                _scroll_to_bottom(page)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(0.5)

            png_bytes = page.screenshot(full_page=True, type="png")
            return Image.open(io.BytesIO(png_bytes)).convert("RGB")
        finally:
            browser.close()


def _scroll_to_bottom(page, step: int = 800, pause: float = 0.25) -> None:
    """Lazy-load 컨텐츠를 강제 로드. 같은 위치가 두 번 측정되면 종료."""
    last = -1
    for _ in range(120):  # 최대 ~30초
        height = page.evaluate("document.body.scrollHeight")
        if height == last:
            break
        page.evaluate(f"window.scrollBy(0, {step})")
        time.sleep(pause)
        last = height

"""클라우드 OCR 프로바이더.

로컬 OCR(PaddleOCR + EasyOCR) 결과 신뢰도가 낮을 때 폴백/대체용.
사용자가 본인 API 키를 입력하는 BYO-key 방식 (배포 시 비용 분담 회피).

현재 지원: Google Cloud Vision (DOCUMENT_TEXT_DETECTION).
의존성 추가 0 — urllib + json (표준 라이브러리)만 사용.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from PIL import Image

from ..core.ocr_engine import OCRLine, OCRResult

log = logging.getLogger(__name__)


class CloudOCRError(Exception):
    """클라우드 OCR 호출 실패. 네트워크/인증/쿼터 등 복합 원인."""


# ── 자동 OCR 정책 (툴바 콤보로 사용자가 즉시 전환) ────────────────────────
POLICY_LOCAL_ONLY = "local_only"            # 클라우드 자동 호출 X (수동 버튼은 그대로)
POLICY_AUTO_FALLBACK = "auto_fallback"      # 로컬 결과 약할 때만 클라우드 (비용 ↓)
POLICY_CLOUD_PREFERRED = "cloud_preferred"  # 키 있으면 무조건 클라우드, 없으면 로컬

VALID_POLICIES = (POLICY_LOCAL_ONLY, POLICY_AUTO_FALLBACK, POLICY_CLOUD_PREFERRED)


@dataclass(frozen=True)
class CloudOCRConfig:
    """QSettings 에서 읽어온 클라우드 OCR 설정 묶음.

    `policy` 는 자동 OCR 동작 모드 (툴바 콤보에서 즉시 전환 가능).
    수동 '클라우드 인식' 버튼은 정책과 무관하게 동작 (override).
    """
    enabled: bool = False
    provider: str = "google_vision"
    google_api_key: str = ""
    policy: str = POLICY_AUTO_FALLBACK

    def is_ready(self) -> bool:
        """선택된 프로바이더 호출에 필요한 설정이 다 갖춰졌는지."""
        if not self.enabled:
            return False
        if self.provider == "google_vision":
            return bool(self.google_api_key.strip())
        return False


class CloudOCRProvider:
    """클라우드 OCR 프로바이더 공통 인터페이스."""
    name: str = "abstract"

    def recognize(self, image: Image.Image) -> OCRResult:  # noqa: D401
        raise NotImplementedError


class GoogleVisionProvider(CloudOCRProvider):
    """Google Cloud Vision (DOCUMENT_TEXT_DETECTION).

    API 키만 있으면 호출 가능 (서비스 계정 JSON 불필요).
    자세한 응답 포맷: https://cloud.google.com/vision/docs/reference/rest/v1/images/annotate
    """
    name = "google_vision"
    _ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
    _TIMEOUT_SEC = 30
    _LANG_HINTS = ["ko", "en"]

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise CloudOCRError("Google Vision API key is empty")
        self._api_key = api_key

    def recognize(self, image: Image.Image) -> OCRResult:
        body = self._build_request_body(image)
        try:
            data = self._post(body)
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                err_body = ""
            log.error("Google Vision HTTP %d: %s", exc.code, err_body[:500])
            raise CloudOCRError(f"HTTP {exc.code}: {err_body[:200]}") from exc
        except urllib.error.URLError as exc:
            log.error("Google Vision network error: %s", exc)
            raise CloudOCRError(f"네트워크 오류: {exc.reason}") from exc
        except Exception as exc:  # noqa: BLE001
            log.exception("Google Vision unexpected error")
            raise CloudOCRError(str(exc)) from exc

        return _parse_google_vision_response(data)

    # ── internals ────────────────────────────────────────────────────
    def _build_request_body(self, image: Image.Image) -> bytes:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG", optimize=False)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        payload = {
            "requests": [{
                "image": {"content": b64},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                "imageContext": {"languageHints": self._LANG_HINTS},
            }],
        }
        return json.dumps(payload).encode("utf-8")

    def _post(self, body: bytes) -> dict:
        url = f"{self._ENDPOINT}?key={self._api_key}"
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._TIMEOUT_SEC) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))


def _parse_google_vision_response(data: dict) -> OCRResult:
    """Google Vision 응답을 OCRResult 로 변환.

    DOCUMENT_TEXT_DETECTION 응답의 fullTextAnnotation.text 가 이미 단락 구조 잘 정리됨.
    한 줄짜리 OCRLine 으로 감싸 본 파이프라인의 _format_text 를 그대로 통과시킴.
    """
    responses = data.get("responses") or []
    if not responses:
        return OCRResult(lines=[])

    response = responses[0] or {}

    err = response.get("error")
    if err:
        raise CloudOCRError(err.get("message") or "Unknown Google Vision error")

    full = response.get("fullTextAnnotation")
    if not full:
        return OCRResult(lines=[])

    text = (full.get("text") or "").strip()
    if not text:
        return OCRResult(lines=[])

    # 블록별 confidence 의 산술 평균. 없으면 보수적으로 0.95 (Google 일반 신뢰도).
    confs: list[float] = []
    for page in full.get("pages") or []:
        for block in page.get("blocks") or []:
            c = block.get("confidence")
            if isinstance(c, (int, float)) and c > 0:
                confs.append(float(c))
    avg_conf = sum(confs) / len(confs) if confs else 0.95

    # 단일 OCRLine 으로 감쌈 — Google 의 \n 이 그대로 보존되어 UI 에 표시됨.
    return OCRResult(lines=[OCRLine(text=text, confidence=avg_conf, box=[])])


def make_provider(config: CloudOCRConfig) -> CloudOCRProvider | None:
    """config 에 맞는 프로바이더 생성. 설정 미흡 시 None."""
    if not config.is_ready():
        return None
    if config.provider == "google_vision":
        return GoogleVisionProvider(config.google_api_key)
    log.warning("Unknown cloud OCR provider: %s", config.provider)
    return None

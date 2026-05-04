# SnipOCR

윈도우 스니핑 도구 스타일의 스크린샷 OCR 도구. Windows + macOS 데스크톱 지원.

## 기능

- **전체화면 OCR** — 모든 모니터를 합친 가상 화면을 한 번에 캡처해 인식
- **구역 OCR** — 화면을 어둡게 덮고 드래그로 사각형 영역만 선택해 인식
- **웹페이지 스크롤 OCR** — URL을 입력하면 백그라운드 Chromium이 풀페이지를 캡처해 인식

OCR 엔진은 **PaddleOCR (한국어 + 영어 혼용 모델)** 을 오프라인으로 사용합니다.

## 단축키

| 동작 | Windows | macOS |
|------|---------|-------|
| 전체화면 OCR | `Ctrl + Shift + 1` | `Cmd + Shift + 1` |
| 구역 OCR     | `Ctrl + Shift + 2` | `Cmd + Shift + 2` |
| 웹페이지 OCR | `Ctrl + Shift + 3` | `Cmd + Shift + 3` |

트레이 아이콘 우클릭 메뉴로도 모두 실행 가능합니다.

## 개발 환경 설정

```bash
# Python 3.10 ~ 3.12 권장
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

python main.py
```

첫 실행 시 PaddleOCR 모델(약 10MB)이 자동 다운로드됩니다. 이후로는 인터넷 없이 동작합니다.

### macOS 권한 안내

처음 실행하면 다음 권한이 필요합니다.

1. **화면 녹화** (시스템 설정 > 개인정보 보호 및 보안 > 화면 녹화)
2. **입력 모니터링** (글로벌 단축키용 — 시스템 설정 > 개인정보 보호 및 보안 > 입력 모니터링)

## 빌드 (단일 실행 파일)

```bash
pip install pyinstaller

# Windows
pyinstaller build/build_windows.spec --clean --noconfirm

# macOS
pyinstaller build/build_mac.spec --clean --noconfirm
```

빌드 산출물은 `dist/SnipOCR/` (Windows) 또는 `dist/SnipOCR.app` (macOS)에 생성됩니다.
PaddleOCR + paddlepaddle + Chromium 의존성 때문에 결과물은 약 300~500MB입니다.

## 프로젝트 구조

```
src/
├── app.py                # 메인 컨트롤러 (트레이/단축키/오버레이 연결)
├── core/
│   ├── ocr_engine.py     # PaddleOCR 래퍼
│   ├── capture.py        # mss 화면 캡처
│   └── browser_capture.py# Playwright 풀페이지 캡처
├── ui/
│   ├── overlay.py        # 구역 선택 오버레이
│   ├── result_window.py  # OCR 결과 창
│   ├── url_input.py      # URL 입력 다이얼로그
│   └── tray.py           # 시스템 트레이 아이콘
└── utils/
    ├── platform_utils.py # Win/Mac 분기
    ├── hotkeys.py        # pynput 글로벌 단축키
    └── clipboard.py      # 클립보드 헬퍼
```

## 추가된 기능 (`src/features/`)

- **QR 인식** (`features/barcode.py`) — OpenCV QR 디텍터 기본. `pyzbar` 설치 시 1D 바코드까지 인식. 결과창에 별도 패널로 표시.
- **자동 전처리** (`features/preprocess.py`) — UI 노출 없이 백그라운드 적용:
  - 어두운 배경(흰 글자/검은 배경 터미널) 자동 감지 후 색반전
  - 텍스트 기울어짐 자동 보정 (감지 시에만)
  - 음영/조명 불균일 사진은 자동 적응형 이진화 (스크린샷처럼 깨끗한 이미지는 건너뜀)

## 향후 추가 예정

- OCR 히스토리 (SQLite)
- 번역 연동 (DeepL / Papago)
- 표 인식 (PaddleOCR PP-Structure)
- 수식 인식 (pix2tex / LaTeX)

각 기능은 `src/features/` 아래 모듈로 추가하면 기존 코드 변경 없이 결합 가능합니다.

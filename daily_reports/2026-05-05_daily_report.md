# Daily Report - 2026-05-05

## 프로젝트: OCR (SnipOCR)
Windows 스니핑 도구 스타일의 스크린샷 OCR 데스크톱 유틸리티. PySide6 + PaddleOCR + EasyOCR 앙상블로 한국어 인식, deep-translator로 번역, SQLite 히스토리, iOS 26 스타일 UI.

---

## 완료한 작업

### 1. 원격 레포 머지 + 로컬 git 셋업

기존에 있던 작업 폴더를 비우고 GitHub `jay-twiggy/OCR`의 `claude/screenshot-ocr-tool-0cKQe` 브랜치를 `main`에 머지 → 로컬을 `git init` + `pull origin main`으로 연결.

- `git clone` (임시 폴더) → `git merge --no-ff origin/claude/screenshot-ocr-tool-0cKQe` → `git push origin main`
- 머지 커밋: `9911672 Merge branch 'claude/screenshot-ocr-tool-0cKQe' into main`
- gh CLI 미설치라 직접 `git`만으로 PR 없이 단순 머지 처리

---

### 2. OCR 엔진 안정화 (PaddleOCR 3.x 호환성 + 정확도)

#### 2-1. PaddleOCR 3.5.0 API 변경 대응

설치된 PaddleOCR이 3.5.0인데 코드는 2.x용으로 작성되어 있어 첫 실행부터 망가짐. 여러 단계의 수정.

- `src/core/ocr_engine.py`:
  - `show_log=False` 인자 제거 (3.x에서 삭제됨 — `Unknown argument: show_log` 에러)
  - `use_angle_cls` → `use_textline_orientation` 으로 자동 폴백
  - `predict()` API 사용, `_parse_v3_result()` 신규 파서 추가 (`rec_texts`/`rec_scores`/`rec_polys` 필드)
  - `_construct_paddle()` — 인자 호환성 단계적 폴백 (4단계 시도)

#### 2-2. paddlepaddle OneDNN 버그 회피

`NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support` 에러로 추론 자체가 실패.

```python
os.environ.setdefault("FLAGS_use_mkldnn", "false")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "false")
```

`main.py` 진입점에서 환경변수 + `enable_mkldnn=False` 생성자 인자로 OneDNN 백엔드 비활성화.

#### 2-3. 자동 업스케일 (정확도 결정타)

작은 캡처(682×136 한국어 뉴스)에서 OCR 정확도가 처참 (avg_conf 0.311, garbage 텍스트). 가설 검증한 결과:

| 테스트 | lines | avg_conf |
|---|---|---|
| 원본 (682×136) | 4 | **0.311** (garbage) |
| 그레이스케일 변환 | 4 | 0.266 (더 나빠짐) |
| **2x 업스케일 (1364×272)** | 14 | **0.650** |
| **자동 업스케일 (4012×800)** | 30 | **0.947** ✓ |

→ `_maybe_upscale()` 추가: 짧은 변이 800px 미만이면 LANCZOS 보간으로 800px 기준 업스케일. PaddleOCR이 max_side 4000 초과하면 자동 클립.

#### 2-4. 박스 좌표 정규화

업스케일된 이미지의 OCR 박스를 다시 원본 이미지 좌표로 다운스케일.

```python
scale_x = w0 / w1; scale_y = h0 / h1
if scale_x != 1.0 or scale_y != 1.0:
    for line in lines:
        line.box = [(x * scale_x, y * scale_y) for x, y in line.box]
```

소비자(UI)는 항상 원본 이미지 좌표만 보면 됨.

#### 2-5. Korean server 모델 시도 → 실패 → 원복

`korean_PP-OCRv5_server_rec` 모델 시도했으나 **존재하지 않음** ("No engine bindings registered"). 다국어 통합 `PP-OCRv5_server_rec`은 사실상 중국어 전용으로 한글 인식률 폭락 (avg_conf 0.91 → 0.65, "号品", "35人2" 같은 중국어 오인식).

→ 결론: PaddleOCR 내에서 `korean_PP-OCRv5_mobile_rec`이 한국어 최선. 더 나은 정확도는 다른 엔진 추가만이 길.

---

### 3. OCR 결과 후처리 (단락 복원)

PaddleOCR이 업스케일된 이미지에서 단어 단위로 박스를 분리하는 경향 → 결과창에 단어마다 줄바꿈으로 표시되는 문제.

#### 3-1. Y좌표 그룹핑 + 단락 병합 (`_format_text`)

- **1단계 — 시각적 줄 묶기**: Y좌표 근접(box_height × 0.6 이내) 박스를 같은 라인으로 묶음
- **2단계 — 단락 병합**: 시각적 줄 사이의 Y갭이 line_height × 0.8 이내 + 이전 줄이 "꽉 찬 줄" + 이전 줄이 종결 부호로 끝나지 않을 때만 병합

#### 3-2. CJK-aware 결합 (`_join_continuation`)

- 영문 등 라틴 wrap: 공백으로 결합 (`"the boy" + "ran"` → `"the boy ran"`)
- 한자/한글/일본어 인접: **공백 없이** 결합 (`"이어지" + "는 문장"` → `"이어지는 문장"`)
- 영문 hyphenation: `"es-" + "tablish"` → `"establish"`

```python
_THOUGHT_TERMINATORS = ".!?。!?)]}」』』〕〉》｝~…"

def _ends_with_terminator(text: str) -> bool:
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in _THOUGHT_TERMINATORS
```

검증: 한국 뉴스 기사 (3 단락 wrap) → 3 단락 정확히 복원 / 불릿 리스트 5개 → 5개 정확히 분리.

---

### 4. 앙상블 OCR (PaddleOCR + EasyOCR 병렬)

PaddleOCR mobile 단독으로는 한계. EasyOCR을 보조 엔진으로 추가하고 병렬 실행 후 더 나은 결과 채택.

#### 4-1. 새 엔진 래퍼 (`src/core/easyocr_engine.py`)

- PyTorch CPU 기반, 한글/영어 모델 자동 다운로드
- PaddleOCR과 동일한 `OCRResult` 인터페이스 노출
- 초기화 실패 시 `instance()`가 None 반환 (안전 폴백)

#### 4-2. ThreadPoolExecutor 병렬 실행

```python
with ThreadPoolExecutor(max_workers=2) as pool:
    paddle_future = pool.submit(_paddle)
    easy_future = pool.submit(_easy)
    ...
```

#### 4-3. 결과 선택 — `_pick_best_result()` 휴리스틱

처음에 avg_conf로 비교했더니 PaddleOCR(0.91)이 EasyOCR(0.43)을 늘 이겼지만, **실제 텍스트 품질은 EasyOCR이 더 정확** (PaddleOCR: "걸이큰앉은", EasyOCR: "성과급으로"). 두 엔진의 conf는 척도가 달라 직접 비교 불가.

→ **글자 수(text coverage)** 1차, conf 2차로 변경:

```python
if abs(diff) > 0.10:  # 글자 수 격차 10%p 초과
    return more_chars_winner
else:
    return higher_conf_winner  # 차이가 적을 때만 conf
```

검증: 동일 캡처에서 EasyOCR 정확히 선택됨 (`chars=206 > paddle=145`).

설치 이슈: easyocr가 opencv-python-headless를 요구해 cv2.pyd 잠금 충돌 → `--no-deps`로 우회 + torch/torchvision 별도 설치.

---

### 5. 번역 기능 (`src/features/translate.py`)

`deep-translator` (Google 무료 웹 백엔드, API 키 불필요) 통합.

- 4500자 청크 분할 (Google 5000자 제한 마진)
- 비동기 `_TranslateWorker` (QThread)
- 10개 언어 지원, **한국어/영어/중국어/일본어 우선 순서**:
  ```python
  LANG_LABELS = {"ko": "한국어", "en": "영어", "zh-CN": "중국어(간체)", "ja": "일본어",
                 "zh-TW": "중국어(번체)", "es": "...", "fr": "...", ...}
  ```
- `QSettings`로 마지막 선택 언어 영구 저장
- 결과창 텍스트 패널 아래쪽에 번역 영역 추가 (감지 시만 표시)

---

### 6. 자동 전처리 + 자동 업스케일

#### 6-1. `src/features/preprocess.py` — 자동 적용 (UI 토글 없음)

- **자동 디스큐**: minAreaRect 기반 각도 추정, 0.5°~20° 범위에서만 보정
- **자동 이진화**: 처음에 추가했다가 **클린 디지털 텍스트도 트리거되어 OCR 망가짐** → 제거. `_binarize()` 함수는 수동 호출용으로 보존.

#### 6-2. 자동 색반전 (다크모드 OCR) — 추가했다 제거

다크 터미널 OCR을 위해 `_maybe_invert()` 추가했으나, 사용자가 "다크 모드 관련 처리 모두 제거" 요청 → 제거. 향후 다크 캡처는 OCR 정확도 떨어짐 (사용자 받아들임).

---

### 7. 확장 기능 (`src/features/`)

#### 7-1. QR/바코드 인식 (`barcode.py`)

- `pyzbar` 시도 → Windows VC++ runtime 의존성 문제 (libzbar-64.dll 로딩 실패) → **OpenCV `QRCodeDetector`로 전환** (이미 있는 cv2)
- pyzbar는 선택 의존성으로 남김 (설치 + DLL 로딩 가능 시 1D 바코드까지 자동 활성화)

#### 7-2. 진단 로깅 (`src/utils/logger.py`)

- `logs/snipocr.log` (RotatingFileHandler, 1MB×5)
- OCR 매번 `logs/last_capture.png` 저장 (덮어쓰기)
- 결과 미리보기 + avg_conf 로그 → "OCR이 받은 입력"과 "출력"을 직접 검증 가능

---

### 8. 히스토리 (SQLite + 좌측 사이드바)

#### 8-1. 저장소 (`src/features/history.py`)

- `logs/history.db` SQLite 단일 파일
- 캡처 이미지: `logs/captures/<timestamp>.png` 별도 파일 (DB는 경로만)
- 외부 의존성 0 (Python 표준 `sqlite3`)
- 스키마: `id, created_at, mode, source_url, image_path, text, avg_confidence, engine, translation_target, translation_text`

#### 8-2. UI 통합 (옵션 A → B → C 진화)

- **A안 시도**: 좌측 패널에 [원본 | 히스토리] 탭 — 미사용
- **B안 채택 (Phase 5)**: 좌측 = 항상 히스토리, "원본 보기" = 모달
- **C안 (디자인 핸드오프)**: 좌측 = 히스토리 + [원본 | 결과] 토글 → 우측 디테일 영역 스왑 — **최종**

#### 8-3. 동작

- OCR 완료 시 자동 저장 + 리스트 갱신
- 항목 클릭 → 텍스트/번역/이미지 즉시 로드 (재OCR 없음)
- 우클릭 메뉴: 삭제 / 모두 삭제

---

### 9. UI Phase 1 — 좌/우 구조 (NavigationSplitView 스타일)

- 좌측: SnipOCR 타이틀 + **세그먼티드 토글 [원본 | 결과]** + 검색바 + 히스토리 리스트
- 우측: `QStackedWidget` (결과 뷰 / 원본 뷰) — 토글로 전환
- 신규 위젯: `_SegmentedToggle`, `_FitImageLabel` (KeepAspectRatio 자동 스케일)

### 10. UI Phase 2 — 디자인 토큰 + 시각 스타일링 (`src/ui/styles.py`)

- iOS 26 컬러/타이포 토큰 한 곳에 통합 (`TINT`, `LABEL`, `LABEL_SECONDARY`, `SURFACE_*`, `FILL_*`, `SEPARATOR`)
- `apply_app_font(app)` — SF Pro / Segoe UI / Malgun Gothic 폴백 체인
- **플로팅 글래스 툴바**: 반투명 + 라운드 14px + `QGraphicsDropShadowEffect`
- **+ 새 OCR CTA**: 그라데이션 + 글로우 펄스 (`QPropertyAnimation` on `blurRadius`, 14↔28, 2.6초 사이클 무한 반복)
- 모든 패널 16px 라운드 카드, 일관된 패딩

### 11. UI Phase 3 — 인터랙션 위젯 (`src/ui/feedback.py`)

신규 위젯들:

- **`Toast`**: 캡슐형, ✓ 그린 아이콘, 자동 페이드아웃 (1.8초 후 `QPropertyAnimation`)
- **`BusyOverlay`**: 다크 백드롭 + 가운데 흰 카드 + 커스텀 회전 링 스피너 (`QPainter`)
- **`NewOCRSheet`**: 모달 시트, 그래버 + 옵션 그리드 + 취소; 외부 클릭 자동 닫기
- 헬퍼 `show_toast(parent, text)`

### 12. UI Phase 4 — 디텍션 박스 (추가 → 제거)

`_FitImageLabel.paintEvent`에 박스 + hover 배지 그리는 로직 추가했으나 사용자가 "정보바 신뢰도면 충분, 박스는 빼" 요청 → 제거. 박스 좌표 정규화 로직은 유용해서 OCREngine에 보존.

### 13. UI Phase 5 — 싱글 윈도우 + 파일 OCR

#### 13-1. 싱글 윈도우 리팩토링

- `LauncherWindow` **삭제** (별도 창 불필요)
- `ResultWindow.load_new_image(image, mode, source_url)` — **창 재활용**으로 새 이미지 로드 + 자동 OCR
- `closeEvent` 오버라이드 → 트레이로 숨김 (앱 종료는 트레이 메뉴)
- `app.py`에 `self._main_window` 단일 인스턴스, 모든 캡처가 같은 창에서 갱신

#### 13-2. 파일에서 OCR (`src/features/file_loader.py`)

- 이미지: PIL.Image.open
- PDF: `pymupdf` 첫 페이지 200dpi 렌더링 (다중 페이지면 안내 메시지)
- 시트 옵션 추가 → 4개 (전체화면/구역/웹페이지/파일에서) 2x2 그리드

### 14. UI Phase 6 — 헤더 분리 + 인라인 툴바 + 5:5 + iOS 스크롤바

- `QToolBar` 완전 제거
- **상단 헤더** (`#topHeader`): "SnipOCR" 라벨, 40px 높이
- **인라인 툴바** (`#inlineToolbar`): 우측 패널 안쪽 상단 고정 (토글 무관)
  - [복사] [저장] [이미지] [다시 OCR] | [번역] [한국어 ▾] ··· [+ 새 OCR]
- OCR 텍스트 ↔ 번역 패널 **5:5 비율** (둘 다 stretch=1)
- **iOS 스크롤바** 전역 적용 (얇은 10px, 라운드, 반투명 회색, hover 시 진해짐)

---

### 15. 기타 / 진단

- **다크모드 추가 → 완전 제거**: 사용자 "한 가지 버전만 사용" 결정 후 모든 다크 관련 처리 삭제
- **Phase 6 검증 후 MVP 마무리**: 사용자 "마음에 든다, MVP는 이정도면 충분"
- **배포 프로세스 안내**: PyInstaller spec → Inno Setup → 코드 서명 → GitHub Releases 단계별 흐름 + 산출물 크기/시간 추정

---

## 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `main.py` | **수정** | OneDNN 우회 환경변수 + 로깅 init + sys.excepthook |
| `requirements.txt` | **수정** | easyocr, deep-translator, pymupdf 추가 (paddleocr는 그대로) |
| `.gitignore` | **수정** | `logs/` 추가 |
| `README.md` | **수정** | 추가 기능 섹션 갱신 |
| `src/app.py` | **수정** | 싱글 윈도우 리팩토링, 파일 OCR 핸들러, 글로벌 폰트 적용 |
| `src/core/ocr_engine.py` | **수정** | PaddleOCR 3.x 호환, 자동 업스케일, 박스 정규화, 단락 병합, 진단 저장 |
| `src/core/easyocr_engine.py` | **신규** | EasyOCR 래퍼 (싱글톤 + None 폴백) |
| `src/features/__init__.py` | **신규** | features 패키지 |
| `src/features/barcode.py` | **신규** | OpenCV QR 디텍터 + pyzbar 옵셔널 |
| `src/features/preprocess.py` | **신규** | 자동 디스큐 (이진화는 수동용) |
| `src/features/translate.py` | **신규** | deep-translator 래퍼 + 청크 분할 |
| `src/features/history.py` | **신규** | SQLite 히스토리 저장소 |
| `src/features/file_loader.py` | **신규** | 이미지/PDF 로더 (pymupdf 첫 페이지) |
| `src/utils/logger.py` | **신규** | 회전 파일 로거 + stderr |
| `src/ui/result_window.py` | **수정** | 대규모 리팩토링: 좌/우 분할, 토글, 검색, 인라인 툴바, 헤더, 결과/원본 스택, 번역 패널, 히스토리 리스트, BusyOverlay, NewOCRSheet 연동 |
| `src/ui/launcher_window.py` | **삭제** | 싱글 윈도우 전환 후 불필요 |
| `src/ui/tray.py` | **수정** | "창 표시" 메뉴 + 시그널, 다크 모드 관련 코드 제거 |
| `src/ui/styles.py` | **신규** | iOS 26 디자인 토큰 + 공통 QSS + 전역 스크롤바 |
| `src/ui/feedback.py` | **신규** | Toast, BusyOverlay, NewOCRSheet (그래버 + 2x2 그리드) |

---

## 기술적 결정 사항

### 1) PaddleOCR Korean 모델: mobile 유지
PaddleOCR 3.5.0의 모델 레지스트리(293개) 전수조회 결과 한국어 server 변종이 **존재하지 않음**. 다국어 통합 `PP-OCRv5_server_rec`은 사실상 중국어 전용으로 한국어 인식률 폭락. 따라서 PaddleOCR 내에서 가능한 최선은 mobile. 정확도 향상은 EasyOCR 같은 외부 엔진 추가만이 길.

### 2) 두 엔진 결과 비교: 글자 수 1차, conf 2차
PaddleOCR conf와 EasyOCR conf는 척도가 달라 직접 비교 불가 (PaddleOCR 0.91이 EasyOCR 0.43보다 더 정확하다고 단정 못 함). 실측: PaddleOCR이 더 작은 영역에 단어들을 짧은 fragment로 잘게 인식하고, EasyOCR은 라인 단위로 더 길게 인식. **더 많은 글자를 인식한 쪽 = 일반적으로 더 정확**. 단, 격차가 10%p 이내면 conf로 결정.

### 3) 자동 업스케일 임계값: 800px
짧은 변이 800px 미만이면 LANCZOS로 800px 기준 비율 유지 업스케일. 검증: 800px 미만에서 OCR 정확도 폭락 (avg_conf 0.31 → 0.95). PaddleOCR이 max_side 4000을 넘으면 자체 클립하므로 안전.

### 4) 단락 병합 휴리스틱: 3-요소 AND
같은 단락 조건은 (a) Y갭 작음 + (b) 이전 줄이 꽉 찬 줄 + (c) 이전 줄이 종결 부호로 끝나지 않음 — 모두 충족할 때만. 셋 중 하나만 깨져도 새 단락. 이유: 불릿 리스트는 (b) 또는 (c)에서 걸리고, wrap된 기사 단락은 셋 다 통과.

### 5) 디텍션 박스 제거
구현했지만 사용자가 정보바의 "N개 영역" + 평균 신뢰도면 충분하다 판단. 시각적 노이즈 줄이고 단순화. 박스 좌표 정규화 로직은 OCREngine에 보존 (향후 활용 여지).

### 6) 다크모드 완전 미지원
사용자 "한 가지 버전만 사용" 결정. 시스템/사용자 지정 모두 안 함. 다크 캡처 OCR도 지원 포기 (auto-invert 제거). UI 코드 단순화 효과.

### 7) 싱글 윈도우 + 트레이 상주
별도 런처 창 제거. ResultWindow가 메인 창 + 트레이 아이콘. 닫기 [X]는 트레이로 숨김. 종료는 트레이 메뉴에서만. 히스토리가 항상 좌측에 보이므로 다중 창 불필요.

---

## 오늘의 인사이트 (Lessons & Insights)

### 💡 기술 인사이트

- **PaddleOCR 3.x는 2.x 코드와 호환되지 않음** `tags: paddleocr, breaking-changes, ocr`
  `show_log` 인자 제거, `use_angle_cls` → `use_textline_orientation` 리네임, 출력 포맷 변경(`rec_texts`/`rec_scores`/`rec_polys` dict). `paddleocr>=2.7.0` 같은 broad pin은 위험. `paddleocr>=3.0.0`로 명시 + 코드는 3.x용으로 작성하거나, 양쪽 호환되도록 try/except 폴백 필요.

- **OCR 정확도는 입력 해상도에 매우 민감** `tags: ocr, preprocessing, paddleocr, easyocr`
  검출 모델은 글자 높이가 일정 픽셀 이상일 때만 제대로 동작. 작은 캡처(짧은 변 < 200px)에서 정확도 폭락 (avg_conf 0.31 → 자동 업스케일 후 0.95). **OCR 전 자동 업스케일은 필수**. ClearType 서브픽셀 렌더링 가설은 틀렸음 (그레이스케일 변환은 도움 안 됨).

- **paddlepaddle Windows OneDNN 백엔드는 PIR 미지원 케이스 있음** `tags: paddlepaddle, windows, runtime`
  `ConvertPirAttribute2RuntimeAttribute not support` 에러는 OneDNN(MKLDNN) 백엔드의 PIR(Paddle Intermediate Representation) 미구현 케이스. 환경변수 + 생성자 인자로 OneDNN 끄면 회피 (CPU 약간 느려지지만 안전):
  ```python
  os.environ["FLAGS_use_mkldnn"] = "false"
  os.environ["FLAGS_enable_pir_in_executor"] = "false"
  PaddleOCR(..., enable_mkldnn=False)
  ```

- **이종 OCR 엔진 conf는 직접 비교 불가** `tags: ensemble, ocr, heuristics`
  PaddleOCR conf(0.91)가 EasyOCR conf(0.43)보다 높아도 실제 텍스트 정확도는 EasyOCR이 더 좋을 수 있음. 엔진별로 conf 측정 방식이 다름. **글자 수(text coverage)** 또는 **편집 거리** 같은 텍스트 자체 메트릭으로 비교해야 함.

- **deep-translator의 GoogleTranslator는 5000자 제한** `tags: translation, deep-translator`
  큰 OCR 결과는 청크 분할 필요. 단락 단위 그리디 분할로 4500자 마진 두면 안전. 결합 시 단락 구조 보존.

- **OpenCV `cv2.QRCodeDetector`는 시스템 의존성 0** `tags: qr-code, opencv, windows`
  `pyzbar`는 Windows에서 libzbar-64.dll + VC++ 2013 runtime 필요해서 첫 사용자가 설치 실패하기 쉬움. opencv-python의 내장 `QRCodeDetector`는 이미 cv2가 있으면 추가 의존성 0. 1D 바코드까지 필요한 경우만 pyzbar 옵셔널로.

### 🚫 실패한 접근법 (Anti-patterns)

- **자동 이진화: "음영 감지" 휴리스틱 = 사실상 텍스트 밀도 측정** `tags: preprocessing, heuristics, anti-pattern`
  "글자-배경 차이 분산이 크면 음영 있음 → 이진화"로 구현했더니, **글자가 빽빽한 클린 디지털 텍스트일수록 트리거됨**. 깨끗한 안티앨리어싱이 깨져 OCR 정확도 폭락. 글자 밀도와 음영 그라디언트는 같은 통계적 신호로 안 보임. 자동 이진화는 위험하니 OFF가 기본, 수동 토글로만.

- **server 모델은 무조건 mobile보다 정확하지 않음** `tags: paddleocr, models, anti-pattern`
  "server 모델 = 정확도 ↑"라고 가정하고 `PP-OCRv5_server_rec`로 교체했더니 한국어 → 중국어로 오인식. 다국어 표방하지만 사실상 중국어 위주 모델. 항상 **언어별 전용 모델 우선 → 그 안에서 server vs mobile 비교**.

- **avg_conf만으로 결과 선택** `tags: ensemble, ocr, anti-pattern`
  처음에 `_pick_best_result`를 avg_conf 비교로 구현 → 항상 PaddleOCR이 이김 → 사용자는 EasyOCR이 더 정확한 결과를 못 봄. 척도 다른 두 시스템의 자체 신뢰도를 비교하는 건 의미 없음. **출력 자체의 품질 지표(글자 수, 단어 수, 단어 사전 매칭률)로 비교**해야 함.

- **합성 테스트 이미지로 OCR 정확도 회귀 검증** `tags: testing, ocr, anti-pattern`
  Pillow `ImageDraw.text()`로 합성한 영문 단락 이미지는 줄 끝 X좌표가 들쭉날쭉(87%, 88%, 94%) → "꽉 찬 줄" 휴리스틱이 거짓 양성으로 단락을 쪼갬. 실제 웹 캡처는 column-justified로 wrap된 줄들이 모두 95%+ 도달. **OCR 휴리스틱은 합성 이미지로 회귀 검증하면 잘못된 신호 줄 수 있음**. 실제 캡처본을 회귀 데이터셋으로 보존.

### 🎯 프로덕트 인사이트

- **다크 모드는 검증이 매우 어렵고 가치는 비대칭적** `tags: ux, dark-mode, mvp-strategy`
  코드 추가 → 사용자 시점 검증 → 또 다른 엣지 케이스 → 결국 "한 가지 버전만 쓸래"로 회귀. 다크 캡처 OCR도 같은 패턴 (auto-invert 추가 → 잘못된 케이스에서 트리거 → 제거). MVP에서 다크 모드 도입 비용은 ROI 낮음. 라이트 단일로 시작 → 사용자가 진짜로 요청할 때만 추가.

- **+ 새 OCR 시트 옵션은 4개 이상이면 그리드 레이아웃** `tags: ux, layout, modal-sheet`
  3 옵션 한 줄(QHBoxLayout) → 4 옵션 추가 시 옆으로 더 늘리지 말고 2x2 그리드(QGridLayout)로. 시각적 균형 좋고 모바일 친화적.

- **싱글 윈도우 + 좌측 히스토리 = 멀티 윈도우보다 압도적 우위** `tags: ux, window-management`
  매 OCR마다 새 창 띄우면 화면 어수선함. 좌측 히스토리에서 항목 클릭으로 과거 결과 불러오기가 자연스러움. 결과창 = 메인 창 + 트레이 상주 패턴이 데스크톱 유틸 best-practice.

- **OCR 결과 + 번역 = 5:5 비율이 가장 자연스러움** `tags: ux, layout`
  처음에 OCR 텍스트 stretch=2, 번역 stretch=1로 했다가 번역이 작게 나옴. 사용자는 보통 번역을 같이 보고 비교하므로 동등 비중이 옳음.

### 🔗 프로젝트 횡단 연결

- **로깅 + 디버그 이미지 저장 = 사용자 환경 디버깅의 마법** `tags: logging, debugging, cross-project`
  사용자 환경에서만 발생하는 OCR garbage 문제를 진단하기 위해 `logs/last_capture.png` (덮어쓰기) + `avg_conf` + `preview` 로그를 추가했더니 즉시 원인 파악(해상도 부족). **OCR/이미지/오디오 처리 같은 도메인은 입력/출력을 디스크에 항상 저장 + 핵심 메트릭 로그가 필수**. FoodLens 같은 다른 비전 프로젝트에서도 동일 패턴 적용 가능.

- **iOS 디자인 토큰 시스템(`styles.py`)은 다른 PySide6 앱에 그대로 이식 가능** `tags: design-system, pyside6, cross-project`
  컬러/타이포/QSS를 한 모듈에 정리 + `apply_app_font` 함수형 진입점. 다른 데스크톱 유틸 만들 때 `styles.py`만 복사 + 컴포넌트 위에 적용으로 일관된 iOS 룩 즉시 확보.

- **Y좌표 + 종결부호 + 줄 길이 3-신호 단락 복원** `tags: ocr, nlp, text-layout`
  OCR뿐 아니라 PDF 추출, 스캔본 처리 등에서 동일 문제 발생. `_format_text` 휴리스틱은 다른 텍스트 추출 도메인에 그대로 적용 가능.

---

## 주요 상수 / 수치 정리

| 항목 | 값 | 설명 |
|------|-----|------|
| `_MAX_CHUNK_CHARS` (translate) | 4500 | Google 번역 5000자 제한 마진 |
| 자동 업스케일 임계값 | 800px (짧은 변) | OCR 검출 모델 최소 입력 크기 |
| 단락 Y갭 임계값 | line_height × 0.8 | 단락 분리 기준 |
| 단락 "꽉 찬 줄" tolerance | 5% (또는 30px) | 줄 끝이 컬럼 우측에 도달 판정 |
| 시각적 줄 그룹 임계값 | line_height × 0.6 | 같은 줄 박스 묶기 |
| 토스트 자동 닫힘 | 1800ms | 페이드아웃 280ms |
| CTA 글로우 펄스 | 14↔28px, 2.6s | InOutSine, 무한 반복 |
| 기본 번역 언어 | ko (한국어) | 사용자 환경 기본 |
| 자동 색반전 luma 임계값 | 110 | (제거됨, 다크 모드 미지원) |
| `min_confidence` (텍스트 필터) | 0.2 | 노이즈 박스 컷오프 |

---

## TODO / 다음 단계

### 🔴 우선순위 높음
- [ ] PyInstaller `*.spec` 파일 작성 (Windows + macOS)
- [ ] OCR 모델 사전 번들링 (PaddleOCR `~/.paddlex/`, EasyOCR `~/.EasyOCR/`)
- [ ] Playwright Chromium 번들 + `PLAYWRIGHT_BROWSERS_PATH` 설정
- [ ] 깨끗한 PC에서 dist 폴더 더블클릭 실행 검증

### 🟡 중간 우선순위
- [ ] Inno Setup 스크립트 작성 (Windows 설치파일)
- [ ] 시작 시 자동 실행 옵션 (트레이 상주)
- [ ] VC++ Redist 자동 동봉
- [ ] GitHub Releases 첫 배포 (zip 압축 폴더부터)
- [ ] 코드 서명 검토 (예산/배포 규모 따라)

### 🟢 기타 / 장기
- [ ] PDF 다중 페이지 처리 (현재 첫 페이지만)
- [ ] 다른 번역 엔진 (DeepL/Papago API 키 입력)
- [ ] 풀스크린 모드 / 단축키 추가
- [ ] macOS 빌드 (DMG + 코드 서명 + 공증)
- [ ] 자동 업데이트 메커니즘 (`pyupdater` 등)
- [ ] OCR 히스토리 검색 인덱싱 (FTS5)

---

**수집 범위**: 2026-05-04T00:30:00+09:00 ~ 2026-05-05T00:30:00+09:00
**작성시각**: 2026-05-05T00:30:00+09:00
**작성자**: Jay-Park

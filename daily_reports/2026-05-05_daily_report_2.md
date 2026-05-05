# Daily Report - 2026-05-05 (오후/저녁 — 패키징 사이클)

## 프로젝트: OCR (Binave OCR)
PaddleOCR + EasyOCR 앙상블 + iOS 26 스타일 PySide6 UI를 갖춘 Windows/macOS 데스크톱 OCR 유틸리티.
이번 리포트는 **MVP를 다른 사람에게 줄 수 있는 형태로 패키징**한 사이클을 다룬다.

> 참고: 같은 날 새벽에 작성된 [2026-05-05_daily_report.md](./2026-05-05_daily_report.md) 가 MVP 핵심 기능(앙상블 OCR, 번역, 히스토리, iOS UI 등)을 다루며, 그 작업은 commit `c009afc` 로 박혔다. 본 리포트는 그 이후 패키징 + 리브랜딩 + UI 마이크로-폴리시 작업만 다룬다.

---

## 완료한 작업

### 1. SnipOCR → Binave OCR 일괄 리브랜딩 (commit `bf2e6e3`)

프로젝트 이름 전환. **디스플레이/바이너리/로거**라는 세 가지 컨텍스트에 맞게 이름 체계를 분리하여 일관 적용.

#### 1-1. 이름 체계

| 컨텍스트 | 사용 이름 | 이유 |
|----------|-----------|------|
| 디스플레이 (윈도우 타이틀, 트레이 툴팁, 헤더, 사이드바) | `Binave OCR` | 공백 포함 자연어 |
| 바이너리 / Python 클래스 (`BinaveOCRApp`, `BinaveOCR.exe`, `BinaveOCR.app`) | `BinaveOCR` | shell escape 회피 + CamelCase 관습 |
| 로거 / 로그 파일 (`binave_ocr.main`, `logs/binave_ocr.log`) | `binave_ocr` | Python snake_case 관습 |

#### 1-2. 변경 범위

총 9개 파일 17곳:
- `src/__init__.py` — docstring + `__version__`
- `main.py` — logger name, 시작 로그 메시지
- `src/app.py` — `class BinaveOCRApp`, `setApplicationName`, `setOrganizationName`, `setWindowTitle`, `app = BinaveOCRApp()`
- `src/utils/logger.py` — log path → `logs/binave_ocr.log`
- `src/ui/result_window.py` — `_SETTINGS_ORG/APP`, `setWindowTitle("Binave OCR — 결과")`, 헤더 라벨, 사이드바 타이틀
- `src/ui/styles.py` — docstring
- `src/ui/tray.py` — `setToolTip`
- `src/ui/feedback.py` — (이번 변경엔 없음, 다른 commit에서)
- `src/features/__init__.py` — docstring
- `README.md` — 제목 + 산출물 경로

**의도적으로 보존**:
- `design_handoff/design_handoff_snipocr_ios/` — 외부에서 받은 핸드오프 패키지 (출처 추적성)
- `daily_reports/2026-05-05_daily_report.md` — 과거 작성 시점 기록

#### 1-3. 사이드 이펙트

- `_SETTINGS_ORG/APP` 변경으로 사용자가 마지막으로 선택했던 번역 언어(QSettings 저장)가 초기화되어 기본 `ko`로 돌아감 — 첫 배포 전이라 무관

---

### 2. 우측 패널 그라데이션 UI (commit `bf2e6e3`)

핸드오프 스펙(README.md:61)대로 `linear-gradient(135deg, #e8eef7, #f3e8ee, #fef3e6)` 를 적용. 사용자 피드백: "오른쪽 패널이 너무 화이트 배경이라 심심해".

#### 2-1. 진단

`styles.py` 에 `WALLPAPER_GRADIENT` 토큰은 정의되어 있었으나 **어디에서도 사용 안 됨**. 우측 패널의 `DETAIL_CONTAINER_QSS` 는 이미 반투명(`rgba(255,255,255,0.55)`)이었는데, 부모(루트 캔버스)가 흰 배경이라 비치는 효과 없이 흰색으로만 보였음.

#### 2-2. 해결

루트 캔버스(central widget)에 `WALLPAPER_GRADIENT` 적용 → 자식 패널들의 반투명이 자연스럽게 비치는 iOS Liquid Glass 패턴.

```python
# src/ui/result_window.py - _build_ui()
central = QWidget(self)
central.setObjectName("rootCanvas")
central.setStyleSheet(S.ROOT_CANVAS_QSS)
```

```python
# src/ui/styles.py - 신설 토큰
ROOT_CANVAS_QSS = f"QWidget#rootCanvas {{ background: {WALLPAPER_GRADIENT}; }}"
```

`#rootCanvas` ID selector 사용 — 자식 위젯에 스타일 cascade되는 걸 차단.

#### 2-3. 사이드바 투명도 조정

핸드오프 스펙(`rgba(242,242,247,0.72)`)에 맞춰 사이드바 투명도를 0.92 → 0.72로 낮춤. 그라데이션이 사이드바 영역에서도 비침.

```python
# src/ui/styles.py
SURFACE_SIDEBAR = "rgba(242, 242, 247, 0.72)"  # 핸드오프 스펙: 그라데이션이 비치게
```

---

### 3. PyInstaller 빌드 시스템 (commit `bf2e6e3`)

Windows self-contained dist 생성 인프라 1차 구축. PyInstaller 6.20.0 설치 + spec + runtime hook.

#### 3-1. 환경 점검

빌드 전 사전 캐시 확인:
- `~/.paddlex/official_models/` — PaddleOCR 모델 (수십 MB, 다국어)
- `~/.EasyOCR/model/` — EasyOCR 모델 (~95MB)
- `~/AppData/Local/ms-playwright/chromium-*` — Playwright Chromium

dev 환경에서 `import paddleocr` 직접 시도 시 `torch shm.dll` 로딩 에러 발견 — main.py 통한 정상 실행과 빌드에는 영향 없어 보류 (dev 환경 별개 이슈).

#### 3-2. spec 파일 (`build/build_windows.spec`)

핵심 구조:
```python
HOME = pathlib.Path.home()
PADDLEX_DIR = HOME / ".paddlex"
EASYOCR_DIR = HOME / ".EasyOCR"
PLAYWRIGHT_DIR = HOME / "AppData" / "Local" / "ms-playwright"

# 빌드 전 사전 검증
_missing = [...]  # 캐시 누락 체크 → SystemExit
if _missing: raise SystemExit(...)

datas = [
    (str(PADDLEX_DIR), '_bundled/.paddlex'),
    (str(EASYOCR_DIR), '_bundled/.EasyOCR'),
    (str(PLAYWRIGHT_DIR), '_bundled/ms-playwright'),  # 1차 — 전체 통째 (3GB 산출물 원인)
]

binaries = []
for pkg in ('paddle', 'torch', 'torchvision', 'cv2'):
    binaries += collect_dynamic_libs(pkg)

hiddenimports = [...] + collect_submodules('paddle') + collect_submodules('paddleocr') + ...

a = Analysis([str(PROJECT_ROOT / 'main.py')], ...,
             runtime_hooks=[str(SPEC_DIR / 'rthook_set_paths.py')],
             excludes=['tkinter', 'matplotlib', 'IPython', 'jupyter', ...])
```

주요 결정:
- `--onedir` 모드 (onefile 보다 첫 실행 빠름, 압축 해제 비용 없음)
- `upx=False` (paddlepaddle .dll 호환성)
- `console=False` (GUI 모드)
- `--workpath build/_pyi_work` 으로 PyInstaller 임시 산출물을 spec/hook과 격리

#### 3-3. 런타임 훅 (`build/rthook_set_paths.py`)

frozen 환경에서 번들된 모델/Chromium 위치를 사용자 홈으로 시드하거나 환경변수로 가리킴:

```python
def _setup_bundled_paths() -> None:
    if not getattr(sys, "frozen", False):
        return
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    bundled = bundle_dir / "_bundled"

    # 모델: 사용자 홈 시드 (수십 MB, 일회성 복사 OK)
    _seed_dir(bundled / ".paddlex", Path.home() / ".paddlex")
    _seed_dir(bundled / ".EasyOCR", Path.home() / ".EasyOCR")

    # Chromium: 환경변수로 직접 가리키기 (250MB → 복사 회피)
    pw_dir = bundled / "ms-playwright"
    if pw_dir.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(pw_dir)
```

**시드 vs 환경변수 결정 기준**: 모델은 작고 라이브러리가 환경변수 인식 일관성이 부족 → 시드. Chromium은 크고 PLAYWRIGHT_BROWSERS_PATH가 표준 → 환경변수.

#### 3-4. 첫 빌드 결과

- ✅ exit 0, `dist/BinaveOCR/BinaveOCR.exe` 76MB 생성
- ✅ 사용자 더블클릭 검증 OK ("잘 되는군~!")
- ⚠️ **3.0GB** — 예상(700MB-1.2GB)보다 훨씬 큼

---

### 4. Playwright 슬림화 — A안 적용 (commit `50800b4`)

3.0GB 분포 분석으로 **Playwright 폴더 1.3GB가 중복 + 미사용**임을 발견. 동적 필터로 920MB 절감.

#### 4-1. 분포 분석

| 항목 | 크기 | 처리 |
|------|------|------|
| `_bundled/ms-playwright/chromium-1217` | 408MB | ✅ 보존 (browser_capture.py 가 사용) |
| `_bundled/ms-playwright/chromium-1208` | 394MB | ❌ 구버전 — 자동 업데이트 잔재 |
| `_bundled/ms-playwright/chromium_headless_shell-1217` | 266MB | ❌ headless 전용 빌드, 미사용 |
| `_bundled/ms-playwright/chromium_headless_shell-1208` | 259MB | ❌ headless + 구버전 |
| `_bundled/ms-playwright/ffmpeg-1011` | 3.4MB | ✅ 보존 |
| `_bundled/ms-playwright/winldd-1007` | 260KB | ✅ 보존 |
| `_internal/paddle/` | 346MB | 라이브러리 자체 (필수) |
| `_internal/torch/` | 323MB | 라이브러리 자체 (필수) |

#### 4-2. spec에 동적 필터 추가

```python
def _select_playwright_assets() -> list[tuple[str, str]]:
    """ms-playwright 폴더에서 필요한 항목만 선별 번들."""
    if not PLAYWRIGHT_DIR.exists():
        return []
    keep_prefixes = ('chromium-', 'ffmpeg-', 'winldd-')
    latest: dict[str, pathlib.Path] = {}
    for child in PLAYWRIGHT_DIR.iterdir():
        if not child.is_dir():
            continue
        for prefix in keep_prefixes:
            # 'chromium-' 와 'chromium_headless_shell-' 는
            # 하이픈/언더스코어로 자동 구분
            if child.name.startswith(prefix):
                cur = latest.get(prefix)
                if cur is None or child.name > cur.name:
                    latest[prefix] = child
                break
    selected = sorted(latest.values(), key=lambda p: p.name)
    for p in selected:
        print(f"[spec] playwright bundle: {p.name}", file=sys.stderr)
    return [(str(p), f"_bundled/ms-playwright/{p.name}") for p in selected]
```

핵심 트릭: `chromium-` (하이픈) 으로 startswith 체크하면 `chromium_headless_shell-` (언더스코어)는 자동 매칭 안 됨. 별도 exclude 체크 불필요.

#### 4-3. 결과

| 지표 | 1차 빌드 | 2차 빌드 | 절감 |
|------|----------|----------|------|
| 산출물 | 3.0GB | **2.1GB** | 920MB (30%) |
| ms-playwright | 1.3GB | 411MB | 889MB |

build.log 검증 라인:
```
[spec] playwright bundle: chromium-1217
[spec] playwright bundle: ffmpeg-1011
[spec] playwright bundle: winldd-1007
```

---

### 5. Inno Setup 설치파일 (commit `c8f2347`)

PyInstaller dist를 사용자 친화적 Setup .exe로 패키징. `installer/binave_ocr.iss` 작성.

#### 5-1. .iss 핵심 설정

```ini
#define MyAppName       "Binave OCR"
#define MyAppShortName  "BinaveOCR"
#define MyAppVersion    "0.1.0"

[Setup]
AppId={{9A35EC33-1415-486A-ADC8-1D98EE971D49}  ; 고정 GUID — 변경 금지
DefaultDirName={userpf}\{#MyAppShortName}      ; %LOCALAPPDATA%\Programs\BinaveOCR
PrivilegesRequired=lowest                       ; UAC 권한 prompt 회피
PrivilegesRequiredOverridesAllowed=dialog       ; 사용자가 시스템 전체 설치 선택 가능
Compression=lzma2/normal                        ; ultra 보다 빠름, zip 보다 압축률 ↑
OutputDir=dist
OutputBaseFilename=BinaveOCR-Setup-{#MyAppVersion}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Flags: unchecked
Name: "startmenu"   ; (기본 ON)
Name: "autostart"; Description: "Windows 시작 시 자동 실행 (트레이 상주)"; Flags: unchecked

[Files]
Source: "..\dist\BinaveOCR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
; autostart 선택 시 HKCU\...\Run 에 등록 (관리자 권한 불필요)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppShortName}"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart
```

주요 결정:
- **사용자 단위 설치** (`{userpf}` + `PrivilegesRequired=lowest`) — UAC 권한 prompt 회피로 설치 마찰 ↓
- **AppId 고정 GUID** — 향후 v0.1.1, v0.1.2 등 업그레이드 시 Windows가 같은 앱으로 인식 (덮어쓰기 설치 가능). 한 번 정하면 절대 변경 금지
- **lzma2/normal** 압축 — ultra는 빌드 시간 ↑↑, zip은 압축률 ↓
- **다국어**: 한국어 + 영어, 시스템 로케일 자동 감지

#### 5-2. .gitignore 보강

```diff
-build/
+/build/*
+!/build/*.spec
+!/build/*.py
+/installer/dist/
```

PyInstaller workdir + Inno Setup 산출물은 무시하되, `*.spec` / `*.py` / `*.iss` 같은 빌드 정의는 추적.

#### 5-3. ISCC 위치 추적

`winget install JRSoftware.InnoSetup` 후 ISCC.exe 찾는 데 시간 소요. 결국 사용자 단위 설치 위치 발견:
```
C:\Users\pjw88\AppData\Local\Programs\Inno Setup 6\ISCC.exe
```
**not** `C:\Program Files (x86)\Inno Setup 6\` — winget 6.x 부터 user-scope 선호.

#### 5-4. 컴파일 결과

```
Successful compile (177.125 sec)
installer/dist/BinaveOCR-Setup-0.1.0.exe   749MB
```

압축률: 2.1GB → 749MB (~36%, lzma2 효과 좋음)

#### 5-5. 사용자 검증

사용자가 직접 더블클릭 → 마법사 진행 → 설치 → 실행까지 모두 OK ("설치하고 동작까지 잘 되는구나~"). **v0.1.0 패키징 사이클 완료**.

---

### 6. 번역 결과 복사 버튼 + iOS Tinted Button 스타일 (commit `33e3948`)

다음 버전(v0.1.1) 누적 기능 1번. 사용자 요청: "번역한 결과물도 복사하기 버튼이 있으면 좋겠다. 번역창 바로 위, OCR 결과화면 바로 아래, 우측."

#### 6-1. 헤더 위젯 도입

기존 `_translate_label` (단순 QLabel) 단독 배치를 **헤더 위젯**(좌측 라벨 + 우측 [복사] 버튼)으로 재구성.

```python
# src/ui/result_window.py - _build_text_panel()
self._translate_label = QLabel("번역", panel)
self._translate_label.setStyleSheet(...)

self._translate_copy_btn = QPushButton("복사", panel)
self._translate_copy_btn.setMinimumHeight(30)
self._translate_copy_btn.setMinimumWidth(64)
self._translate_copy_btn.setCursor(Qt.PointingHandCursor)
self._translate_copy_btn.setStyleSheet(S.TINTED_BUTTON_QSS)
self._translate_copy_btn.clicked.connect(self._copy_translation)

translate_header_layout = QHBoxLayout()
translate_header_layout.setContentsMargins(0, 0, 0, 0)
translate_header_layout.setSpacing(8)
translate_header_layout.addWidget(self._translate_label)
translate_header_layout.addStretch(1)
translate_header_layout.addWidget(self._translate_copy_btn)

self._translate_header = QWidget(panel)
self._translate_header.setLayout(translate_header_layout)
```

#### 6-2. 헬퍼 + 슬롯

```python
def _set_translation_visible(self, visible: bool) -> None:
    """번역 헤더(라벨 + 복사 버튼)와 텍스트 박스를 함께 보이거나 숨김."""
    self._translate_header.setVisible(visible)
    self._translate_text.setVisible(visible)

def _copy_translation(self) -> None:
    text = self._translate_text.toPlainText().strip()
    if not text or text in ("번역 중…", "(번역 결과 없음)"):
        return
    copy_text(text)
    show_toast(self, "번역 결과가 클립보드에 복사됨")
```

플레이스홀더 텍스트("번역 중…", "(번역 결과 없음)") 클립보드 복사 차단 — 사용자가 실수로 의미 없는 문자열 복사하지 않게.

#### 6-3. 4개 호출처 일괄 마이그레이션

기존 `_translate_label.show()/hide()` + `_translate_text.show()/hide()` 짝 호출을 모두 `_set_translation_visible(bool)` 헬퍼로 교체:
- `load_new_image` (새 OCR 시작 시 — hide)
- `_load_entry` 번역 있을 때 (히스토리 로드 — show + enable)
- `_load_entry` 번역 없을 때 (히스토리 로드 — hide)
- `_on_translate` (번역 시작 — show + disable)

복사 버튼 활성 상태 관리:
- `_on_translate`: 노출 + `setEnabled(False)` (결과 도착 후 활성)
- `_on_translate_ok`: 결과 있으면 `setEnabled(True)`, 빈 결과면 `setEnabled(False)`
- `_on_translate_failed`: `setEnabled(False)`
- `_load_entry`: 번역 있으면 `setEnabled(bool(text.strip()))`

#### 6-4. iOS Tinted Button 스타일 (`TINTED_BUTTON_QSS`)

기존 `SECONDARY_BUTTON_QSS`(`background: transparent`)는 눈에 안 띄고, `PRIMARY_BUTTON_QSS`(블루 그라데이션)는 과함. 그 사이의 중간 강조 레벨로 `TINTED_BUTTON_QSS` 신설:

```python
# src/ui/styles.py
TINTED_BUTTON_QSS = f"""
QPushButton {{
    color: {TINT};
    background: rgba(0, 122, 255, 0.10);
    border: none;
    border-radius: 12px;
    padding: 5px 16px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: -0.2px;
}}
QPushButton:hover  {{ background: rgba(0, 122, 255, 0.18); }}
QPushButton:pressed {{ background: rgba(0, 122, 255, 0.26); }}
QPushButton:disabled {{ color: {LABEL_TERTIARY}; background: {FILL_QUATERNARY}; }}
"""
```

iOS 26 표준 Tinted Button 패턴 (옅은 tint 배경 + tint 글자색 + 알약). 향후 같은 톤의 다른 버튼에도 재사용.

---

### 7. "다시 인식 중…" → "인식 중…" 라벨 통일 (commit `33e3948`)

사용자 피드백: "OCR 돌리면 돌아가는 동안 '다시 인식 중'이라고 나오는데 '인식 중'으로 바꿔".

#### 7-1. 원인

`BusyOverlay` 클래스의 default 인자가 `"다시 인식 중…"` 으로 작성되어 있었음. 이 오버레이는 **첫 OCR + 재OCR 모두**에서 사용되는데, 라벨이 재OCR을 가정. 첫 OCR 시 사용자에게 "다시?" 의문.

#### 7-2. 수정

```diff
# src/ui/feedback.py:145
- def __init__(self, parent: QWidget, label: str = "다시 인식 중…") -> None:
+ def __init__(self, parent: QWidget, label: str = "인식 중…") -> None:

# src/ui/result_window.py:763
- self._show_busy_overlay("다시 인식 중…")
+ self._show_busy_overlay("인식 중…")
```

두 곳 동시 수정 — default + 호출처 모두.

---

## 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `src/__init__.py` | **수정** | docstring SnipOCR → Binave OCR |
| `main.py` | **수정** | docstring + logger name `binave_ocr.main` + 시작 로그 |
| `src/app.py` | **수정** | `class BinaveOCRApp` + `setApplicationName/OrganizationName/setWindowTitle` |
| `src/utils/logger.py` | **수정** | docstring + log path `logs/binave_ocr.log` |
| `src/ui/result_window.py` | **수정** | rename + central widget `#rootCanvas` 그라데이션 + `_translate_header` (라벨+복사 버튼) + `_set_translation_visible()` 헬퍼 + `_copy_translation()` 슬롯 + "인식 중…" 라벨 |
| `src/ui/styles.py` | **수정** | rename + `SURFACE_SIDEBAR` 0.92→0.72 + `ROOT_CANVAS_QSS` 신설 + `TINTED_BUTTON_QSS` 신설 |
| `src/ui/tray.py` | **수정** | tooltip "Binave OCR — 스크린샷 OCR" |
| `src/ui/feedback.py` | **수정** | BusyOverlay default label "인식 중…" |
| `src/features/__init__.py` | **수정** | docstring rename |
| `README.md` | **수정** | rename + PyInstaller 빌드 절차 + Inno Setup 가이드 |
| `.gitignore` | **수정** | `build/*` 무시 + `*.spec`/`*.py` 보존 + `installer/dist/` 무시 |
| `build/build_windows.spec` | **신규** | PyInstaller spec — `_select_playwright_assets()` 동적 필터 포함 |
| `build/rthook_set_paths.py` | **신규** | frozen 환경 모델 시드 + `PLAYWRIGHT_BROWSERS_PATH` 주입 |
| `requirements-build.txt` | **신규** | `-r requirements.txt` + `pyinstaller>=6.20` |
| `installer/binave_ocr.iss` | **신규** | Inno Setup 6 script (사용자 단위 설치, AppId 고정, 한국어/영어, Tasks) |

빌드 산출물(gitignored, 디스크에만 존재):
- `dist/BinaveOCR/BinaveOCR.exe` + 동봉 폴더 — 2.1GB
- `installer/dist/BinaveOCR-Setup-0.1.0.exe` — 749MB

---

## 기술적 결정 사항

### 1) 이름 체계 3단 분리 (Display / Binary / Logger)
디스플레이(`Binave OCR`), 바이너리·클래스(`BinaveOCR`), 로거·로그파일(`binave_ocr`) 셋으로 분리. 각각의 컨텍스트에서 자연스러운 표기 관습이 다르고, shell escape / Python snake_case 같은 기술적 제약이 다름.

### 2) 그라데이션은 루트에, 패널은 반투명으로
`ROOT_CANVAS_QSS` 를 central widget의 ID selector(`#rootCanvas`)에 적용 → 자식 패널들이 반투명(rgba 0.55~0.72)으로 그라데이션을 비춰 보이는 iOS Liquid Glass 패턴. 우측 패널에 직접 그라데이션을 그리는 옵션 B 보다 디자인 의도에 충실.

### 3) PyInstaller `--onedir` 모드 + UPX 비활성
onefile은 첫 실행 시 압축 해제 비용이 크고, UPX는 paddlepaddle .dll 호환성 이슈가 있음. onedir + UPX off 가 안정적.

### 4) 모델 시드 vs 환경변수 — 크기/이동성 기준
- PaddleOCR/EasyOCR 모델 (수십~95MB): **시드** (사용자 홈에 복사). 이유: 라이브러리가 환경변수 인식 일관성 부족, 작아서 복사 비용 OK
- Playwright Chromium (~250MB): **환경변수** (`PLAYWRIGHT_BROWSERS_PATH`). 이유: 크기 부담 + Playwright 표준 환경변수 지원

### 5) Playwright 동적 필터 — `chromium-` vs `chromium_headless_shell-` 구분
`startswith('chromium-')` 가 하이픈/언더스코어 차이로 자동 구분. 별도 exclude 체크 불필요. 같은 prefix 여러 버전이면 사전식 max(=최신) 만 선택.

### 6) Inno Setup 사용자 단위 설치 (`{userpf}` + `lowest`)
시스템 전체 설치(`{autopf}` + `admin`)는 UAC 권한 prompt 트리거. 사용자 단위 설치는 마찰 없음. 단일 사용자용 데스크톱 유틸엔 사용자 단위가 적합.

### 7) Inno Setup AppId 고정 GUID
`9A35EC33-1415-486A-ADC8-1D98EE971D49` 고정. 향후 v0.1.1+ 업그레이드 시 Windows가 같은 앱으로 인식 (덮어쓰기 설치 가능). **한 번 정하면 절대 변경 금지** — 변경 시 신규 앱으로 인식되어 중복 설치.

### 8) lzma2/normal 압축
ultra는 빌드 시간 ↑↑ (수십 분), zip은 압축률 ↓. normal이 균형. 결과 36% 압축률 (2.1GB → 749MB).

### 9) iOS Tinted Button 토큰 — 강조 레벨 중간
PRIMARY (블루 그라데이션, "+ 새 OCR" 같은 메인 CTA) 와 SECONDARY (transparent, 일반 도구 버튼) 사이에 빈 강조 레벨이 있었음. `TINTED_BUTTON_QSS` 가 그 자리. iOS 26 표준 Tinted Button 패턴.

### 10) 검증 절차 단계별 차등
사용자 결정으로 깨끗한 환경 검증(홈 캐시 백업 등)은 스킵 — 내부 테스트 단계에선 OK. 외부 배포 직전엔 다시 해야 함.

---

## 오늘의 인사이트 (Lessons & Insights)

### 💡 기술 인사이트

- **PyInstaller spec에 동적 데이터 필터링 함수를 두는 패턴** `tags: pyinstaller, packaging, python`
  Playwright 같은 라이브러리는 자동 업데이트로 캐시 폴더에 여러 버전을 누적함 (`chromium-1208`, `chromium-1217`, ...). spec에서 폴더 통째 번들하면 산출물이 GB 단위로 폭증. spec은 그냥 Python 파일이므로 안에 함수를 정의해서 동적으로 필터링 가능 (`_select_playwright_assets()` 처럼). 같은 패턴이 다른 캐시성 디렉토리에도 적용 가능. **결과: 920MB 절감.**

- **QSS `#objectName` ID selector로 스타일 cascade 차단** `tags: pyside6, qss, qt`
  부모 위젯에 `setStyleSheet("QWidget { background: ... }")` 하면 모든 자식 QWidget에 cascade됨. ID selector(`QWidget#rootCanvas { ... }`) 를 쓰면 해당 위젯에만 적용. 그라데이션 같은 배경 스타일은 반드시 ID selector 권장.

- **PyInstaller frozen 환경의 모델 시드 vs 환경변수 결정 기준** `tags: pyinstaller, runtime-hook`
  - 라이브러리가 환경변수 인식 일관성이 좋으면 → 환경변수 (`PLAYWRIGHT_BROWSERS_PATH` 같은)
  - 환경변수 인식이 들쭉날쭉하면 → 사용자 홈으로 시드 (`shutil.copytree`)
  - 결정 보조 기준: **크기**. 250MB+ 는 무조건 환경변수 (복사 비효율). 수십 MB는 시드 OK.

- **Inno Setup AppId GUID는 한 번 정하면 절대 변경 금지** `tags: inno-setup, distribution, windows`
  AppId는 Windows가 "같은 앱의 다른 버전인지" 판단하는 키. v0.1.0 → v0.1.1 업그레이드 시 같은 GUID여야 덮어쓰기 설치 (기존 제거 후 신규 설치 X). 변경하면 신규 앱으로 인식되어 중복 설치 됨.

- **winget 6.x는 사용자 단위(user-scope) 설치 선호** `tags: winget, packaging, windows`
  `winget install JRSoftware.InnoSetup` 결과가 `C:\Program Files (x86)\` 가 아니라 `%LOCALAPPDATA%\Programs\Inno Setup 6\` 에 깔림. ISCC.exe 위치 추적 시 이 경로도 확인할 것. PATH에도 자동 추가 안 됨.

- **`startswith` 의 하이픈/언더스코어 자동 구분** `tags: python, string-matching`
  `'chromium-'` 와 `'chromium_headless_shell-'` 는 첫 9자가 다르므로 (`'-'` vs `'_'`), `startswith('chromium-')` 가 후자를 자동으로 거름. 별도 exclude 체크 불필요. 명명 규칙이 안전한 구분자를 쓸 때 활용 가능한 트릭.

- **`du -sh */` glob은 dot prefix 디렉토리를 못 잡음** `tags: bash, gotcha, unix`
  `*` 는 Unix 관습으로 `.foo` 같은 hidden 디렉토리를 매칭 안 함. 진짜 누락이 아닌데도 출력에 안 나타남. `ls -la` 또는 명시 경로(`du -sh dist/foo/_internal/_bundled/.paddlex`)로 별도 확인 필요. 디렉토리에 `.paddlex` 처럼 점으로 시작하는 항목이 있을 때 함정.

### 🚫 실패한 접근법 (Anti-patterns)

- **PyInstaller spec에서 폴더 통째 번들** `tags: pyinstaller, anti-pattern`
  `(str(PLAYWRIGHT_DIR), '_bundled/ms-playwright')` 처럼 통째 번들하면 캐시성 폴더의 모든 잔재(구버전, headless 변종 등)가 다 들어감. 1차 빌드에서 3.0GB 산출물의 절반이 이 한 줄 때문이었음. **항상 동적 필터 함수 거쳐서 번들 — 폴더 통째는 절대 금지.**

- **PowerShell tool wrapper 출력이 비어 보일 때** `tags: tooling, powershell`
  Claude Code의 PowerShell tool로 `Get-ChildItem -Recurse` 같은 명령을 보내면 출력이 비어 반환되는 경우 종종 발생. Bash로 `powershell -NoProfile -Command "..."` 우회하면 정상 출력. PowerShell tool 자체의 한계로 보임 — 의심되면 즉시 우회.

- **dev 환경에서 `import paddleocr` 직접 시도 → torch DLL 로딩 에러** `tags: paddleocr, torch, dev-env`
  modelscope → torch → shm.dll 의존성 체인에서 로딩 실패. `main.py` 통한 정상 실행 흐름에서는 발생 안 함. dev 환경의 별개 이슈로 빌드/실행에는 영향 없음. **import 검증 시 단순 `import` 보다 실제 진입점(main.py) 실행으로 확인할 것.**

- **단순 라벨 텍스트 버튼은 클릭 가능성을 못 알림** `tags: ui, ux`
  `SECONDARY_BUTTON_QSS` (`background: transparent; border: none`) 만 적용된 버튼은 텍스트만 보여 사용자가 "이게 버튼이야?" 헷갈림. 사용자 피드백 "그냥 '복사'텍스트만 있어서 눈에 잘 안들어와. 버튼처럼 만들어"가 그 증상. 옅은 색 배경(`rgba(tint, 0.10)`)이라도 있어야 어포던스(affordance) 발생.

### 🎯 프로덕트 인사이트

- **검증 절차는 단계별로 깊이 차등** `tags: qa-strategy, pdca`
  내부 테스트 단계에선 깨끗한 환경 시뮬(홈 캐시 백업) 같은 까다로운 검증은 스킵 OK. 외부 배포 직전엔 필수. "다음 사용자가 누구인가" 에 따라 검증 깊이 결정. 모든 단계에 풀 검증 강요하면 진행 속도 ↓.

- **라벨 텍스트는 컨텍스트 무관하게 작성** `tags: ux-copy, i18n`
  "다시 인식 중…" 처럼 특정 시나리오를 가정한 라벨은, 같은 컴포넌트가 다른 시나리오에서도 사용될 때 부자연스러움. "인식 중…" 처럼 동작 자체만 표현하는 게 안전. 컴포넌트 default 라벨은 가장 일반적인 케이스 기준.

- **iOS 26 디자인 시스템의 3단 강조 레벨** `tags: design-system, ios`
  PRIMARY(메인 CTA, 블루 그라데이션) / TINTED(중간 강조, 옅은 tint 배경) / SECONDARY(일반 도구, transparent) 셋이 자연스럽게 분포. 디자인 시스템에 없으면 모두 PRIMARY나 SECONDARY로 몰리고 강조 위계가 무너짐. **Tinted 토큰을 별도 추가하는 게 재사용성 ↑.**

- **다른 사람에게 줄 때 SmartScreen 경고 안내가 필수** `tags: distribution, ux, windows`
  코드 서명 안 한 PyInstaller 산출물은 첫 실행 시 "Windows에서 PC를 보호했습니다" 파란 화면 발생. 받는 사람이 놀라거나 실행 포기할 수 있음. 메시지 템플릿에 "추가 정보 → 실행" 클릭 안내를 명시. 정식 배포 전엔 코드 서명($200~300/년) 검토.

### 🔗 프로젝트 횡단 연결

- **PyInstaller spec의 동적 필터 패턴은 모든 데스크톱 Python 앱에 재사용 가능** `tags: pyinstaller, reusable-pattern, desktop-app`
  `_select_playwright_assets()` 같은 동적 필터는 다른 캐시성 폴더(예: `~/.cache/huggingface`, `~/AppData/Local/torch_extensions`) 번들에도 그대로 적용 가능. 핵심: **번들 대상은 결정론적으로 선별, 자동 누적되는 폴더는 통째 번들 금지.** 향후 FoodLens 데스크톱 버전이나 다른 Python 데스크톱 앱 패키징 시 그대로 차용.

- **Inno Setup `binave_ocr.iss` 템플릿** `tags: inno-setup, template, windows-distribution`
  사용자 단위 설치 + 한국어/영어 multi-lang + Tasks(데스크톱/시작메뉴/자동시작) + AppId 고정 + lzma2 압축 — 이 조합은 한국 Windows 사용자 대상 어떤 데스크톱 앱에도 그대로 복사해서 변수 4개(MyAppName/Version/ShortName/ExeName + AppId GUID)만 바꾸면 즉시 사용 가능. **iss 파일 자체를 템플릿 자산으로 보관할 가치 있음.**

- **빌드 스크립트와 빌드 산출물의 .gitignore 분리** `tags: gitignore, build-system`
  `/build/*` + `!/build/*.spec` + `!/build/*.py` 패턴은 PyInstaller 외에 다른 빌드 도구(예: webpack, esbuild)에서도 같은 컨셉으로 적용 가능. **빌드 정의(spec/config)는 git, 빌드 산출물(dist/work)은 ignore** — 모든 프로젝트의 기본 패턴으로 강제할 가치.

---

## 배포 현황

| 항목 | 상태 | 비고 |
|------|------|------|
| `dist/BinaveOCR/` PyInstaller 산출물 | ✅ 빌드 완료 | 2.1GB, 사용자 GUI 검증 OK |
| `installer/dist/BinaveOCR-Setup-0.1.0.exe` | ✅ 컴파일 + 설치 검증 완료 | 749MB, 사용자 직접 설치 + 동작 확인 |
| 깨끗한 환경 검증 (홈 캐시 백업) | ⏭️ 스킵 (내부 테스트만) | 외부 배포 직전 다시 해야 함 |
| GitHub Release 페이지 | ⏳ 대기 중 | v0.1.1 추가 기능 통합 후 |
| 코드 서명 인증서 | ⏳ 대기 중 | 외부 정식 배포 시점 ($200~300/년) |
| macOS 빌드 | ⏳ 대기 중 | 별도 Mac 환경 필요 (PyInstaller 크로스 컴파일 불가) |

---

## 주요 상수 / 수치 정리

| 항목 | 값 | 설명 |
|------|-----|------|
| `MyAppVersion` | `0.1.0` | `installer/binave_ocr.iss` + `src/__init__.py.__version__` 동기화 필수 |
| `AppId` GUID | `9A35EC33-1415-486A-ADC8-1D98EE971D49` | Inno Setup AppId 고정 — 변경 절대 금지 |
| PyInstaller 산출물 크기 | 2.1GB | --onedir, _bundled 729MB + 라이브러리 1.37GB |
| Setup .exe 크기 | 749MB | lzma2/normal 압축, ~36% 압축률 |
| Playwright trim 절감 | 920MB | 3.0GB → 2.1GB |
| `SURFACE_SIDEBAR` opacity | `0.72` | 핸드오프 스펙 (`rgba(242,242,247,0.72)`), 이전 0.92 |
| `WALLPAPER_GRADIENT` | `linear-gradient(135deg, #e8eef7, #f3e8ee, #fef3e6)` | 핸드오프 스펙 정확치 |
| `TINTED_BUTTON_QSS` 배경 | `rgba(0,122,255,0.10)` (hover 0.18, pressed 0.26) | iOS 26 Tinted Button |
| 빌드 시간 (PyInstaller) | ~5-7분 | dev 환경 1회 |
| 빌드 시간 (Inno Setup) | 177초 (3분) | lzma2/normal |

---

## TODO / 다음 단계

### 🔴 우선순위 높음
- [ ] 사용자가 알려줄 v0.1.1 추가 기능 목록 받기 → 구현
- [ ] v0.1.1 패키징: `__version__` + `MyAppVersion` 두 곳 동기화 → PyInstaller 재빌드 → Inno Setup 재컴파일

### 🟡 중간 우선순위
- [ ] 깨끗한 환경 검증 (외부 배포 직전): `~/.paddlex` / `~/.EasyOCR` 임시 백업 → 인터넷 차단 → exe 실행 → 시드 발동 + OCR 동작 확인
- [ ] **B안** 추가 절감 — Qt 미사용 모듈 excludes (Qt3D/QtCharts/QtMultimedia/QtWebEngine, ~30~50MB 절감)
- [ ] cv2 (148MB) → opencv-python-headless 검토 (GUI 모듈 제외)

### 🟢 기타 / 장기
- [ ] **macOS 빌드** — `build/build_mac.spec` 작성 (Mac 환경 확보 후)
- [ ] **코드 서명 인증서** ($200~300/년) — SmartScreen 경고 회피, 외부 정식 배포 전
- [ ] **GitHub Release** 자동화 — Setup.exe 업로드 + CHANGELOG
- [ ] **자동 업데이트 메커니즘** (`pyupdater` / `tufup` / 자체 구현)
- [ ] PDF 다중 페이지 처리 (현재 첫 페이지만)
- [ ] DeepL/Papago API 옵셔널 (정확도 향상)
- [ ] OCR 히스토리 검색 인덱싱 (FTS5)

---

**수집 범위**: 2026-05-05T00:30:00+09:00 ~ 2026-05-05T21:45:28+09:00
**작성시각**: 2026-05-05T21:45:28+09:00
**작성자**: Jay-Park

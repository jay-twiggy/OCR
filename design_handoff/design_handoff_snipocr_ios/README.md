# Handoff: SnipOCR — iOS 26 리디자인 (A안 / Variant Classic)

## Overview
SnipOCR은 화면을 캡처해 OCR로 텍스트를 추출하고 번역하는 데스크톱 유틸리티입니다. 이 핸드오프는 기존 MVP의 단순한 윈도우 UI를 **Apple iOS / iPadOS 26 (Liquid Glass) 스타일**로 재디자인한 결과물 중 **A안 — iPad 정통 NavigationSplitView** 방향만 골라 정리한 것입니다.

A안의 요지:
- **좌측 사이드바** — 상단에 `원본 / 결과` 세그먼티드 토글, 그 아래 검색바 + 히스토리 리스트(고정).
- **우측 디테일** — 좌측 토글 상태에 따라 두 가지 화면 중 하나를 표시: **결과 뷰**(OCR 원문 + 번역 패널) 또는 **원본 뷰**(캡처 이미지 + 인식 영역 박스 오버레이).
- **상단 플로팅 Liquid Glass 툴바** — 컨텍스트별 액션(복사/저장/번역/다시 OCR 등)을 노출하고, 맨 우측에 컬러 + 글로우가 입혀진 prominent **+ 새 OCR** CTA가 있음.
- 색상은 iOS Tint 시스템 한 가지(기본 Blue `#007AFF`)만 강조색으로 사용. 나머지는 시스템 그레이/라벨 토큰.

## About the Design Files
이 패키지에 들어 있는 파일은 **HTML/JSX로 만든 디자인 레퍼런스**입니다 — 의도된 외형과 인터랙션을 보여주는 프로토타입이지, 그대로 가져다 쓸 프로덕션 코드가 아닙니다.

작업 목표는 **이 HTML 디자인을 대상 코드베이스의 환경(예: Electron + React, Tauri + Svelte, native macOS/Windows, 등)에서 그 코드베이스의 기존 패턴과 라이브러리로 재구현**하는 것입니다. 현재 코드베이스가 정해져 있지 않다면, 데스크톱 OCR 유틸리티에 적합한 스택(Electron + React + TypeScript 등)을 골라 구현하시면 됩니다.

JSX 파일들은 React 18 + Babel standalone에서 돌도록 쓰여 있고, 빌드 시스템 없이도 `SnipOCR Variant A.html`을 브라우저로 열면 그대로 미리볼 수 있게 되어 있습니다.

## Fidelity
**High-fidelity (hifi).** 색상, 타이포그래피, 간격, 모서리 반경, 인터랙션은 모두 의도된 최종 값입니다. iOS 26 디자인 시스템의 토큰을 그대로 참조했고(`assets/colors_and_type.css`), Liquid Glass 효과 스펙(backdrop-blur, 인너 스트로크, 미세한 섀도)도 명시되어 있습니다.

다만 다음은 의도된 placeholder입니다:
- 아이콘은 SF Symbols **풍** SVG입니다(스트로크 1.8–2.2). 실제 빌드에서는 SF Symbols(macOS)나 동등한 스트로크 아이콘셋(Lucide 등)을 사용하세요.
- 우측 "원본 뷰"의 신문기사 미리보기는 mock입니다. 실제로는 사용자가 캡처한 비트맵 이미지가 그 자리에 들어갑니다.
- 히스토리 데이터, 한국어/영어 본문은 샘플 콘텐츠입니다.

---

## Screens / Views

전체 캔버스: **1180 × 820 px** (iPad Pro 가로 정도). 외곽 검정 베젤 4px + 14px 패딩 + 28px 모서리 반경.

### 1. Result View (좌측 토글이 "결과"일 때 — 기본)

#### Layout
```
┌────────────────────────────────────────────────────────────┐
│  Status bar (height 28, 6/22/0 padding)  9:41   100% 🔋    │
├────────┬───────────────────────────────────────────────────┤
│        │  ┌─ Floating Liquid Glass Toolbar (top: 16) ───┐  │
│ LEFT   │  │ 호르무즈 해협 보도          [복사][저장]…  │  │
│ PANE   │  │ 방금 전 · 한국어   [번역][언어▾] [+ 새 OCR]│  │
│ 270px  │  └────────────────────────────────────────────┘  │
│        │                                                    │
│ ─ 토글 │  ┌── OCR 결과 ─────────────────────────────────┐ │
│ ─ 검색 │  │ 미군이 민간 선박의 호르무즈 해협 …           │ │
│ ─ 히스 │  │ (한국어 본문)                                │ │
│   토리 │  └─────────────────────────────────────────────┘ │
│   리스 │                                                    │
│   트   │  ┌── 번역 → 영어 ──────────────────────────────┐ │
│        │  │ While the U.S. military …                    │ │
│        │  │ (영문 번역)                                  │ │
│        │  └─────────────────────────────────────────────┘ │
│        │                                                    │
│        │     ─ Home indicator (bottom 6, w200×h5)         │
└────────┴───────────────────────────────────────────────────┘
```

배경 (Tweak `background`):
- `wallpaper` — `assets/ipad-light.jpg` 사진 월페이퍼 풀블리드
- `gradient` (기본) — `linear-gradient(135deg, #e8eef7 0%, #f3e8ee 50%, #fef3e6 100%)`
- `solid` — `#eef0f4`

#### Components

**Status bar** (zIndex 50, pointerEvents none)
- 높이 28, padding `6px 22px 0`, 좌측 "SnipOCR" / 가운데 "9:41" / 우측 100% + 배터리 글리프
- Font `600 14px/1 SF Pro`, color `#000`

**Left pane** — `width: 270px`, `padding: 8/12/12`, `flexShrink: 0`
- 배경 `rgba(242,242,247,0.72)` + `backdrop-filter: saturate(180%) blur(40px)`
- 우측 경계선 `0.5px solid var(--separator)` (= `rgba(60,60,67,0.29)`)
- 자식 구조 (세로):
  1. 타이틀 `SnipOCR` (Title 2 — `600 22px/1.2 SF Pro Display`, padding `6/6/4`)
  2. **세그먼티드 토글 [원본 | 결과]** (아래 별도 명세)
  3. **검색바** (placeholder "검색")
  4. **`최근 OCR` 섹션 헤더** (uppercase, `500 11px/1`, letter-spacing `.06em`, color `var(--label-secondary)`, padding `2/10/6`)
  5. **히스토리 리스트** (5개 셀, 아래 별도 명세)

**세그먼티드 토글** (원본 / 결과)
- 컨테이너: position relative, display flex, padding 3, borderRadius 10, background `rgba(118,118,128,.18)`
- 슬라이딩 인디케이터: position absolute, top/bottom 3, width `calc(50% - 3px)`, left가 토글 상태에 따라 `3` 또는 `50%`, transition `left .2s cubic-bezier(.3,.7,.4,1)`, borderRadius 8, background `#fff`, shadow `0 1px 3px rgba(0,0,0,.10), 0 0 0 0.5px rgba(0,0,0,.04)`
- 각 버튼: flex 1, 투명 배경, padding `7/4`, gap 5, font `(active?600:500) 13px/1 SF Pro`, color는 active일 때 `var(--label)` 아니면 `var(--label-secondary)`. 좌측 아이콘은 14px SF.Photo / SF.DocText.

**검색바**
- margin `4/4/8`, padding `7/10`, borderRadius 10, background `rgba(118,118,128,.12)`
- 좌측 검색 글리프(14px) + placeholder text `400 15px/1 SF Pro`, color `var(--placeholder-text)`

**히스토리 리스트 셀** (각 행)
- padding `8/10`, borderRadius 8
- 선택 시: background `color-mix(in srgb, var(--tint) 14%, transparent)`, color `var(--tint)`
- 행 구조:
  - 1줄: 좌측 제목(`600 14px/1.2 SF Pro`, ellipsis nowrap) + 우측 시간(caption 1, opacity .8)
  - 2줄: 미리보기 텍스트 (footnote = `400 13px/1.4 SF Pro`, secondary, ellipsis)
  - 3줄: 좌측 11px 글로브 아이콘 + 언어 라벨 (`500 11px/1`)

샘플 데이터 (5건): `snipocr-shared.jsx`의 `HISTORY` 상수 참조.

---

**Detail container** (`flex: 1`)
- 배경 `rgba(255,255,255,0.55)` + `backdrop-filter: saturate(180%) blur(40px)`
- 위에 floating glass toolbar, 아래에 콘텐츠 영역.

**Floating Glass Toolbar**
- 절대 위치: `top: 16, left: 20, right: 20, zIndex: 10`
- padding 6, borderRadius 14, gap 4
- 배경 `rgba(255,255,255,0.72)`, `backdrop-filter: saturate(180%) blur(40px)`
- 보더 `0.5px solid rgba(255,255,255,0.6)` (Liquid Glass inner stroke)
- 섀도 `0 8px 30px rgba(0,0,0,.10)`
- 자식 (왼쪽 → 오른쪽):
  1. 제목 블록 (제목 `600 14px/1.1`, 부제 footnote, `paddingLeft: 6, paddingRight: 10`, ellipsis nowrap)
  2. flex spacer
  3. ToolBtn × N (컨텍스트별, 아래 참조)
  4. 0.5px hairline divider (`width: 1, alignSelf: stretch, margin: 6/4, background: rgba(60,60,67,.18)`) — 1차 액션과 2차 액션 사이
  5. 언어 풀다운 (`{lang} ▾`)
  6. **+ 새 OCR CTA** (Prominent — 별도 명세)

**ToolBtn 공통 스타일**
- display flex, alignItems center, gap `(showLabels?6:0)`, padding `(showLabels?"8/12":"8/10")`
- borderRadius 10, border none, background transparent
- color `var(--tint)` (destructive면 `var(--sys-red)`)
- font `590 14px/1 SF Pro`, letterSpacing `-0.24px`, whiteSpace nowrap, flexShrink 0
- hover: `background: rgba(120,120,128,.10)` (`transition: background .15s`)
- press: opacity 0.4 (Apple HIG borderless press 규칙)

**ToolBtn 목록 (Result view)**
- `복사` (Copy 17px) — 클립보드 복사, 토스트 표시
- `저장` (DocText 17px)
- `이미지` (Photo 17px)
- `다시 OCR` (Redo 17px) — 1.5초 reocr 오버레이
- divider
- `번역` (Translate 17px)
- 언어 풀다운 (`{lang}` 디폴트 "영어")

**ToolBtn 목록 (Source view)**
- `영역 조정` (Crop 17px)
- `원본 보기` (Photo 17px)
- `다시 OCR` (Redo 17px)
- divider
- `이미지 저장` (DocText 17px)

**언어 풀다운 버튼**
- padding `8/11`, borderRadius 10, background `rgba(120,120,128,.12)`, color `var(--label)`
- font `500 14px/1`, gap 6, whiteSpace nowrap, 우측에 `ChevDn` 9px
- 클릭 시 그 아래 메뉴 (top 42, right 0, minWidth 180, padding 6, borderRadius 14, glass 배경)
- 옵션: 영어 / 일본어 / 중국어 (간체) / 스페인어 / 프랑스어
- 각 옵션: padding `8/12`, font `400 15px/1`, 선택된 항목 배경 `rgba(0,0,0,.04)` + 우측에 tint 컬러 체크 글리프

**+ 새 OCR Prominent CTA**
- height 40, padding `0/14/0/11`, borderRadius 12, marginLeft 6
- 배경 `linear-gradient(180deg, var(--tint), color-mix(in srgb, var(--tint) 82%, black))`
- color `#fff`, font `700 15px/1`, letterSpacing `-0.24px`
- gap 6, 좌측 SF.Plus 18px(weight 2.6) + 라벨 "새 OCR"
- 섀도(idle): `0 4px 14px <tint>66, 0 0 0 0.5px color-mix(in srgb, <tint> 60%, white) inset, 0 1px 0 rgba(255,255,255,.35) inset`
- 미세한 펄스: `animation: ctaGlow 2.6s ease-in-out infinite` (brightness 1 ↔ 1.08)
- hover: translateY(-1px) + 강한 글로우 `0 8px 22px <tint>88 …`
- press: `transform: translateY(0) scale(0.97)`
- 클릭 → `New OCR` 모달 시트 표시

**OCR 결과 패널 / 번역 패널** (Result view 내부, 두 개 동등)
- 컨테이너: `flex: 1`, display flex column, minHeight 0, minWidth 0
- 헤더: 좌측 라벨 (uppercase, `var(--footnote)` weight 600, letter-spacing .06em, whiteSpace nowrap; 결과는 secondary color, 번역은 tint), 우측에 13px 별 / 휴지통 아이콘
- 본체: padding `18/22`, borderRadius 16, background `rgba(255,255,255,0.85)`, border `0.5px solid rgba(60,60,67,0.10)`, shadow `0 1px 2px rgba(0,0,0,.04)`, overflow auto
- 본문: `whiteSpace: pre-wrap`, color `var(--label)`, lineHeight 1.55, body type (`400 17px/1.5 SF Pro`)
- reocr 진행 중: opacity 0.4 (`transition: opacity .3s`)

콘텐츠 영역 레이아웃 (Tweak `translationPos`):
- `bottom` (기본) — `flexDirection: column` (위 결과 / 아래 번역)
- `right` — `flexDirection: row`
- `sheet` — 번역 패널은 숨기고 화면 하단에 떠 있는 글래스 시트로 표시

**Home indicator**
- absolute bottom 6, left 50% translateX(-50%), width 200, height 5, background `#000`, opacity .35, borderRadius 3, zIndex 60

### 2. Source View (좌측 토글이 "원본"일 때)

레이아웃은 위와 동일 (좌측 패널, 툴바). 차이는 우측 콘텐츠 영역이 단일 **SourceDetail**로 바뀐다는 점입니다.

**SourceDetail 구조** (세로 flex column, gap 10)

1. **헤더** (display flex, justifyContent space-between, padding `6/4`)
   - 좌측: `원본 캡처` 라벨 (footnote uppercase secondary)
   - 우측: 줌 컨트롤 (− `{zoom}%` +) — padding 3, borderRadius 8, background `rgba(120,120,128,.14)`
     - 버튼: padding `4/8`, color tint, font `600 14px/1`
     - 숫자: font `500 12px/1`, color secondary, minWidth 36, center

2. **캔버스** (flex 1, borderRadius 16, padding 24, display flex center)
   - 배경: `repeating-conic-gradient(#f0f0f3 0 25%, #fafafc 0 50%) 0/24px 24px` (체커보드)
   - border `0.5px solid rgba(60,60,67,.10)`
   - 안쪽에 가짜 캡처 카드: aspect-ratio 4/3, width = `(zoom/100) * 720px`, background #fff, borderRadius 8, shadow `0 12px 30px rgba(0,0,0,.14), 0 0 0 1px rgba(0,0,0,.06)`, position relative overflow hidden
   - 카드 안:
     - 가짜 브라우저 헤더 (height 34, traffic light 3개, URL bar)
     - 신문기사 본문 (h1 + 4문단, font 9px/1.55) — 실제 빌드에서는 비트맵 이미지로 대체
     - **OCR Detection box** 5개 — 본문 위에 absolute로 띄움
       - border `1.5px solid var(--tint)`
       - background `color-mix(in srgb, var(--tint) 8%, transparent)`
       - hover 시 background를 18%로 강조 (`transition: background .15s`)
       - hover 시 박스 위에 `{confidence}%` 라벨 (top -22, padding `2/6`, borderRadius 4, background tint, color #fff, font `600 9px/1.2`)

3. **푸터 정보바** (display flex gap 14, padding `10/14`, borderRadius 12)
   - 배경 `rgba(255,255,255,0.78)`, border `0.5px solid rgba(60,60,67,.10)`
   - font `500 13px/1`, color secondary
   - 항목들 (1px hairline divider로 구분):
     - tint 컬러 + Sparkle 13px + `인식 정확도 98%` (fontWeight 600)
     - `5개 영역 · 312 글자`
     - `화면 캡처 1.png · 1024 × 768`
     - 우측 끝: `방금 전`

### 3. Modal: 새 OCR Sheet
+ 새 OCR 버튼 클릭 시 표시.
- 뒷배경 dim: `rgba(0,0,0,0.35)`, zIndex 50, alignItems flex-end
- 시트: width 560, marginBottom 60, padding `22/22/18`, borderRadius 22
- background `rgba(250,250,252,0.92)` + glass blur
- shadow `0 30px 80px rgba(0,0,0,.30)`
- 상단 grabber: `36×5`, borderRadius 3, color `var(--label-tertiary)`, margin auto/18
- 타이틀 "새 OCR" (Title 2 center) + 부제 footnote
- 3-칼럼 그리드 (gap 10):
  - **화면 캡처** — Crop 28px / `⌘⇧4`
  - **파일에서** — Photo 28px / `이미지·PDF`
  - **카메라** — Scan 28px / `연결된 기기`
- 각 옵션: padding `22/12`, borderRadius 14, background `rgba(118,118,128,.10)`, 세로 정렬, 아이콘 색 tint
- 하단에 `취소` 버튼 — width 100%, padding 14, borderRadius 14, background `rgba(118,118,128,.16)`, font `600 17px/1`

### 4. Toast (스낵바)
복사/저장 성공 시 1.8초간 표시.
- absolute, left 50% bottom 32, transform translateX(-50%), zIndex 40
- padding `12/20`, borderRadius 999 (캡슐), background `rgba(28,28,30,0.85)` + glass blur
- color `#fff`, font `500 15px/1`, gap 10
- 좌측에 13px 체크 글리프 (color `var(--sys-green)` = `#34C759`)
- 시각적 예: `✓ 텍스트가 클립보드에 복사됨`

### 5. Re-OCR 오버레이
다시 OCR 클릭 시 1.5초 동안 화면 위에 모달 떠 있음. OCR 결과/번역 패널은 opacity 0.4로 페이드.
- absolute inset 0, background `rgba(0,0,0,0.18)`, zIndex 35, center
- 카드: padding `20/28`, borderRadius 18, background `rgba(255,255,255,0.85)` + glass blur
- 내부: 24×24 round 스피너 (3px tint solid border, top transparent, `animation: spin .8s linear infinite`) + headline `다시 인식 중…`

---

## Interactions & Behavior

### 좌측 ↔ 우측 동기화
- 좌측 패널 상단 세그먼티드 토글이 우측 디테일 영역의 뷰를 결정합니다.
- `view = 'result'` (기본): 우측에 OCR 결과 + 번역 패널.
- `view = 'source'`: 우측에 원본 캡처 뷰어.
- 토글 슬라이딩 인디케이터의 `left`만 200ms cubic-bezier로 transition. 콘텐츠 자체는 즉시 스왑(현재는 페이드 인 없음 — 필요 시 추가).
- 툴바 좌측의 액션 버튼들도 view에 따라 컨텍스트가 바뀝니다 (Result: 복사/저장/이미지/다시 OCR/번역/언어 / Source: 영역 조정/원본 보기/다시 OCR/이미지 저장).

### 복사 / 저장
- 클릭 → `setToast({text})` → 1800ms 후 `setToast(null)`로 자동 닫힘.

### 다시 OCR
- 클릭 → `setReocr(true)` → 1500ms 후 false. 그동안 결과 패널 opacity 0.4 + 화면 가운데에 스피너.

### 언어 풀다운
- 버튼 클릭 시 `showLangMenu` 토글, 옵션 선택 시 `lang` 갱신 + 메뉴 닫힘.
- 외부 클릭으로 닫는 핸들러는 현재 없음 — 빌드 시 추가 권장 (e.g. `useEffect`로 document mousedown 리스너).

### 새 OCR 시트
- + 새 OCR 클릭 → `showSheet=true`, 뒷배경 클릭 또는 옵션 선택 시 close.
- 실제 빌드에서는 sheet 진입 시 `transform: translateY(100%) → 0` 스프링 애니메이션 추가 권장.

### 줌 컨트롤 (Source view)
- − 클릭: zoom = max(50, zoom - 10)
- + 클릭: zoom = min(200, zoom + 10)
- 캡처 카드의 `width`만 `(zoom/100)*720px`로 변경, transition `width .15s`

### Detection box hover
- 박스 위에 마우스를 올리면 fill이 짙어지고 위에 confidence 배지가 뜸.

### 가능한 향후 인터랙션 (현재 미구현)
- Detection box 클릭 시 해당 텍스트 영역으로 결과 패널 스크롤
- 텍스트 선택 → 박스 하이라이트 (양방향 동기화)
- 사이드바 collapse / expand
- 다크 모드 (CSS는 이미 `data-theme="dark"` 토큰 지원)

---

## State Management

A안에서 필요한 로컬 상태:

```ts
interface VariantClassicState {
  view: 'result' | 'source';      // 좌측 토글 + 우측 콘텐츠
  selected: number;                 // 선택된 히스토리 항목 id
  showLangMenu: boolean;            // 언어 풀다운 열림
  lang: string;                     // 번역 대상 언어 ('영어', '일본어', …)
  toast: { text: string } | null;   // 토스트 메시지 (자동 dismiss)
  showSheet: boolean;               // + 새 OCR 시트
  reocr: boolean;                   // 다시 OCR 진행 중
  zoom: number;                     // 원본 뷰 줌 (50~200)
}
```

Tweak 파라미터 (앱 환경설정 / 사용자 선호로 옮길 수 있음):

```ts
interface Tweaks {
  tint: string;                     // hex (default '#007AFF')
  background: 'wallpaper' | 'gradient' | 'solid';
  toolbarDensity: 'icons' | 'labels';
  translationPos: 'bottom' | 'right' | 'sheet';
}
```

데이터 모델 (실제 앱 연동):

```ts
interface OCRRecord {
  id: number;
  title: string;          // 자동 추출/수동 편집
  capturedAt: Date;
  preview: string;        // 본문 첫 줄
  sourceImage: Blob;      // 캡처 비트맵
  recognized: string;     // OCR 결과
  translation?: { target: string; text: string };
  regions: OCRRegion[];   // detection boxes
  lang: string;           // 'ko-KR' 등
}

interface OCRRegion {
  bbox: [x, y, w, h];     // 원본 이미지 좌표 (px)
  text: string;
  confidence: number;     // 0-100
}
```

---

## Design Tokens

### 색상 (`assets/colors_and_type.css`)

**System (light)**
- `--sys-blue: #007AFF` (디폴트 tint)
- `--sys-red: #FF3B30`
- `--sys-green: #34C759`
- `--sys-orange: #FF9500`
- 그 외: indigo `#5856D6`, purple `#AF52DE`, pink `#FF2D55`, mint, teal, cyan, yellow, brown — `colors_and_type.css` 참조

**Labels (translucent — 핵심)**
- `--label: rgba(0,0,0,0.85)` (primary)
- `--label-secondary: rgba(60,60,67,0.6)`
- `--label-tertiary: rgba(60,60,67,0.3)`
- `--placeholder-text: rgba(60,60,67,0.3)`

**Separator**
- `--separator: rgba(60,60,67,0.29)` (light) / `rgba(84,84,88,0.65)` (dark) — 항상 0.5px 또는 1px

**Liquid Glass**
- 배경: `rgba(255,255,255, 0.55–0.85)` (Ultrathin → Thick)
- backdrop-filter: `saturate(180%) blur(40px)`
- 인너 스트로크: `0.5px solid rgba(255,255,255,0.6)`
- 섀도: `0 8px 30px rgba(0,0,0,0.10)` ~ `0 30px 80px rgba(0,0,0,0.30)` (모달)

**Tint 프리셋** (Tweak 메뉴에서 노출하는 6개)
- Blue `#007AFF` / Indigo `#5856D6` / Purple `#AF52DE` / Orange `#FF9500` / Green `#34C759` / Pink `#FF2D55`

### 타이포그래피
SF Pro Text (≤19px), SF Pro Display (≥20px). 웹에서는 `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif` 폴백 권장.

| 토큰 | 크기/줄간격 | 두께 | 트래킹 |
|---|---|---|---|
| Title 2 | 22px / 1.2 | 600 | -0.26px |
| Headline | 17px / 1.3 | 600 | -0.43px |
| Body | 17px / 1.5 | 400 | -0.43px |
| Callout | 16px / 1.4 | 400 | -0.32px |
| Subhead | 15px / 1.4 | 400 | -0.24px |
| Footnote | 13px / 1.4 | 400 | -0.08px |
| Caption 1 | 12px / 1.3 | 400 | 0 |
| Caption 2 | 11px / 1.3 | 400 | +0.07px |

A안에서 자주 쓰는 변형:
- 툴바 ToolBtn: `590 14px/1`, letterSpacing `-0.24px`
- + 새 OCR CTA: `700 15px/1`, letterSpacing `-0.24px`
- 히스토리 셀 제목: `600 14px/1.2`
- 섹션 헤더 (uppercase): `500 11px/1`, letterSpacing `.06em`

### 간격
8pt base + 4pt half-step. iPhone screen edge inset 16, 그룹 리스트 카드 padding 20.

### 모서리 반경 (squircle, CSS border-radius로 근사)
| 용도 | 값 |
|---|---|
| 작은 컨트롤 (segmented, 검색바) | 8–10 |
| 버튼 / 풀다운 메뉴 | 10–14 |
| 패널 카드 | 16 |
| 시트, 모달 | 18–22 |
| iPad 베젤 inner | 28 |
| iPad outer | 38 |
| 캡슐 (토스트) | 999 |

### 섀도
- Floating glass: `0 8px 30px rgba(0,0,0,0.10)`
- Floating button (idle): `0 4px 14px <tint>66`
- Floating button (hover): `0 8px 22px <tint>88`
- Modal/sheet: `0 30px 80px rgba(0,0,0,0.30)`
- Capture card: `0 12px 30px rgba(0,0,0,0.14)`
- 일반 카드: `0 1px 2px rgba(0,0,0,0.04)`

### 애니메이션
- 스프링 기본 response 0.4s, dampingFraction 0.85
- 토글 인디케이터: `left .2s cubic-bezier(.3,.7,.4,1)`
- ToolBtn hover: `background .15s`
- CTA hover: `transform .12s, box-shadow .12s`
- CTA 글로우 펄스: `ctaGlow 2.6s ease-in-out infinite` (brightness 1 ↔ 1.08)
- 줌 width: `width .15s`
- Spinner: `spin .8s linear infinite`
- Re-OCR fade: `opacity .3s`

---

## Assets
- `assets/colors_and_type.css` — iOS 26 토큰 시스템 (색, 타입, 간격, 머티리얼)
- `assets/ipad-light.jpg` — Liquid Glass 데모용 wallpaper (Apple Design Resources 출처). 실제 프로덕션에선 자체 wallpaper 사용 또는 솔리드 배경 권장.
- 아이콘은 `snipocr-shared.jsx` 안에 인라인 SVG로 들어 있음. 실제 빌드에서는 SF Symbols(macOS) / Lucide / 자체 아이콘셋으로 교체.

## Files

```
design_handoff_snipocr_ios/
├── README.md                       ← 본 문서 (구현 시 단일 진입점)
├── SnipOCR Variant A.html          ← 단독 프리뷰 (브라우저로 바로 열어 확인)
├── variant-classic.jsx             ← A안 React 컴포넌트 전부
├── snipocr-shared.jsx              ← 샘플 데이터 + SF Symbols-style 아이콘
├── assets/
│   ├── colors_and_type.css         ← iOS 26 디자인 토큰 (색/타입/간격/머티리얼)
│   ├── ipad-light.jpg              ← 데모 월페이퍼
│   └── source-screenshot.png       ← 원본 캡처용 mock 이미지
└── screenshots/
    ├── 01-result-view.png          ← 기본 결과 뷰 (한→영 번역)
    ├── 02-source-view.png          ← 원본 캡처 뷰 + 디텍션 박스
    ├── 03-new-ocr-sheet.png        ← + 새 OCR 모달 시트
    └── 04-copy-toast.png           ← 복사 후 토스트
```

### 컴포넌트 매핑

| 파일 | export | 역할 |
|---|---|---|
| `variant-classic.jsx` | `VariantClassic` | 루트 — 상태(view/lang/toast 등) + 좌/우 레이아웃 |
| | `LeftPane` | 좌측 270px 사이드바 (토글/검색/히스토리) |
| | `Pane` | OCR/번역 카드 컨테이너 |
| | `SourceDetail` | 원본 캡처 뷰어 (캔버스 + 디텍션 박스 + 줌) |
| | `DetectBox` | OCR detection 박스 (hover confidence 배지) |
| | `HistoryList` | 좌측 히스토리 리스트 |
| | `NewOCRSheet` | + 새 OCR 모달 |
| | `TranslationSheet` | translationPos='sheet'일 때의 하단 시트 |
| `snipocr-shared.jsx` | `SF` | SF Symbols-풍 SVG 아이콘 (Plus/Copy/Photo/…) |
| | `KO_TEXT` / `EN_TEXT` | 샘플 본문 |
| | `HISTORY` | 5개 샘플 히스토리 |

### Screenshots (참고용)
README와 함께 `screenshots/`에 4장 첨부. 픽셀 스펙은 본문에 모두 명시되어 있으니 스크린샷은 어디까지나 시각 확인용입니다.

## 구현 시 권장사항
1. **컴포넌트 분리**: `LeftPane`, `Toolbar`, `ResultView`, `SourceView`, `NewOCRSheet`, `Toast`, `ReOCROverlay`로 쪼개고, 부모는 `view` 상태와 데이터를 props로 주입.
2. **Liquid Glass 추상화**: `<GlassSurface variant="ultrathin|thin|regular|thick">` 같은 래퍼 컴포넌트로 backdrop-filter + 인너 스트로크 + 섀도를 캡슐화. 다크모드 토큰은 `data-theme="dark"`로 자동 스왑.
3. **아이콘**: macOS 빌드라면 SF Symbols 우선, 그 외엔 Lucide 등 stroke 아이콘셋 사용. 상호 매핑은 SF Symbols → Lucide 표 작성을 권장 (예: `house.fill` → `Home`, `doc.on.doc` → `Copy`, `arrow.clockwise` → `RotateCw`).
4. **다크모드**: light 위주로 만들었지만 `colors_and_type.css`는 다크 토큰도 포함. 시스템 prefers-color-scheme 따라 자동 전환 권장.
5. **접근성**:
   - 모든 버튼에 명확한 `aria-label` (특히 아이콘 onlу 모드).
   - 세그먼티드 토글은 `role="tablist"` + `aria-selected`.
   - 토스트는 `role="status"` `aria-live="polite"`.
   - 풀다운 메뉴는 키보드 네비게이션 (↑↓ Esc Enter) 지원.
6. **국제화**: 한국어 외에도 노출 텍스트는 모두 i18n 키로 추출. 본문(KO_TEXT/EN_TEXT)은 사용자 데이터이므로 i18n 대상 아님.
7. **성능**: backdrop-filter는 CPU/GPU 비용이 큼. 동시에 떠 있는 글래스 surface 수를 제한하고, blur 사이즈를 32–40으로 유지.

# macOS 빌드 가이드 — Mac 없이 GitHub Actions 로 빌드하기

이 문서는 **Mac을 갖고 있지 않은 개발자가 macOS .app + .dmg 산출물을 만들고 배포**하는 전체 과정을 다룹니다. Binave OCR 의 v0.2.0 macOS 빌드 셋업을 기준으로 작성되었으나, 모든 PyInstaller 기반 Python 데스크톱 앱에 그대로 적용 가능합니다.

> **목표 독자**: macOS 빌드 처음 시도하는 Windows/Linux 개발자
> **소요 시간**: 첫 셋업 약 2-3시간 (Apple Developer 가입 시간 제외) + 첫 빌드 ~25분

---

## 📚 목차

1. [전체 그림](#전체-그림)
2. [전제 조건](#전제-조건)
3. [Phase A. Apple Developer 인증서 발급 (Mac 없이)](#phase-a-apple-developer-인증서-발급-mac-없이)
4. [Phase B. GitHub Secrets 등록](#phase-b-github-secrets-등록)
5. [Phase C. 빌드 인프라 코드 (이미 작업한 경우 스킵)](#phase-c-빌드-인프라-코드)
6. [Phase D. 첫 빌드 트리거](#phase-d-첫-빌드-트리거)
7. [Phase E. 친구/베타 테스터에게 전달](#phase-e-친구베타-테스터에게-전달)
8. [부록: 트러블슈팅](#부록-트러블슈팅)
9. [부록: 향후 운영](#부록-향후-운영)

---

## 전체 그림

```
[로컬 Windows]              [Apple]                [GitHub]              [Friend's Mac]
     │                         │                       │                       │
     ├─ OpenSSL 로 CSR 생성    │                       │                       │
     ├──────────────────────► [인증서 발급]            │                       │
     │ ◄──────────────────────┤  .cer                  │                       │
     ├─ .p12 합치기 + base64   │                       │                       │
     ├──────────────────────────────────────────────► [Secrets 등록]           │
     │                                                  │                       │
     ├─ workflow yml + spec push ───────────────────► [Actions: macos runner]   │
     │                                                  ├─ PyInstaller         │
     │                                                  ├─ codesign            │
     │                                                  ├─ notarize ──► Apple │
     │                                                  └─ DMG artifact       │
     │ ◄────────────────────────────────────────────── [Download DMG]          │
     │                                                                          │
     └─ DMG 친구에게 전달 ─────────────────────────────────────────────────────►
                                                                              [설치 + 테스트]
```

핵심 포인트:
- **Mac 본체 불필요** — Apple은 인증서 발급 자체에 Mac을 요구하지 않음
- **PyInstaller 는 macOS 러너 필요** — 그래서 GitHub Actions 의 `macos-latest` 사용
- **친구 Mac은 검증/테스트용** — 빌드는 CI에서, 검증은 친구가

---

## 전제 조건

### 필수
- ✅ **Apple Developer Program 가입** ($99/년, 결제 완료)
- ✅ **GitHub repository (public 권장)**
  - Public: GitHub Actions 무료
  - Private: macos-latest 분당 약 $0.08 (한 빌드 ~25분 = ~$2)
- ✅ **OpenSSL** (Windows의 Git for Windows에 포함, 별도 설치 불필요)
- ✅ **Mac 사용자 베타 테스터 1명** (친구/지인) — 빌드 결과 검증용

### 본인이 가지고 있어야 할 정보
- Apple ID 이메일 (Developer 가입한 계정)
- Apple ID 비밀번호 (App-specific password 발급할 때 필요)

---

## Phase A. Apple Developer 인증서 발급 (Mac 없이)

### A-1. OpenSSL 확인

Git Bash를 열고 (시작 메뉴에서 "Git Bash" 검색):

```bash
which openssl
openssl version
```

출력 예시:
```
/mingw64/bin/openssl
OpenSSL 3.5.4 30 Sep 2025
```

→ 안 보이면 [Git for Windows](https://git-scm.com/download/win) 설치.

### A-2. 비밀키 + CSR (Certificate Signing Request) 생성

Git Bash에서 작업 폴더 만들기:

```bash
cd ~  # 또는 원하는 위치
mkdir apple-cert && cd apple-cert
```

비밀키 생성 (절대 분실하면 안 됨, 분실 시 인증서 폐기 후 재발급해야 함):

```bash
openssl genrsa -out private_key.pem 2048
```

CSR 생성:

```bash
openssl req -new -key private_key.pem -out request.csr
```

**프롬프트 입력값** (예시):

| 항목 | 입력 | 비고 |
|---|---|---|
| Country Name (2 letter code) | `KR` | 국가 코드 |
| State or Province Name | `Seoul` | 또는 본인 거주지 |
| Locality Name | `Seoul` | 도시 |
| Organization Name | `홍길동` | 본인 이름 또는 회사 |
| Organizational Unit | (Enter) | 비워둠 |
| Common Name | `홍길동` | 본인 이름 |
| Email Address | `myemail@example.com` | **Apple Developer 가입 이메일** |
| A challenge password | (Enter) | 비워둠 |
| Optional company name | (Enter) | 비워둠 |

→ 같은 폴더에 `request.csr` 파일 생성됨.

### A-3. Apple Developer 콘솔에서 인증서 생성

1. https://developer.apple.com/account/resources/certificates/list 접속 (Apple ID 로그인)
2. 우측 상단 **"+"** 버튼 클릭
3. **Software** 섹션 → **Developer ID Application** 라디오 선택 → **Continue**
   - ⚠️ "Developer ID Application" 이 안 보이면 본인 계정이 **Account Holder** 권한인지 확인 (멤버십 관리 페이지)
4. **Profile Type** 선택:
   - **G2 Sub-CA (Xcode 11.4.1+)** 권장 — 최신 macOS 호환
5. **Choose File** → 위에서 만든 `request.csr` 업로드 → **Continue**
6. 다음 페이지에서 **Download** 버튼 → `developerID_application.cer` 파일 받음
7. 받은 .cer 파일을 위 작업 폴더 (`apple-cert/`) 로 이동

### A-4. .cer + 비밀키 → .p12 합치기

Git Bash 에서 (작업 폴더에서):

```bash
# .cer (DER 형식) → .pem (PEM 형식) 변환
openssl x509 -in developerID_application.cer -inform DER -out cert.pem -outform PEM

# .pem + 비밀키 → .p12 묶기
openssl pkcs12 -export -inkey private_key.pem -in cert.pem \
  -out certificate.p12 -name "Developer ID Application"
```

마지막 명령어 실행 시 **"Enter Export Password:"** 프롬프트 나옴.

→ 적당히 강한 비밀번호 입력 (예: `MyP12Pass2026!`). **이 비밀번호 메모해두기** — GitHub Secret 에 등록할 때 필요.

→ 같은 폴더에 `certificate.p12` 파일 생성됨.

### A-5. .p12 → base64 인코딩 (GitHub Secret 용)

GitHub Secret 은 텍스트만 받으므로 .p12 (바이너리)를 base64 (텍스트)로 변환.

**PowerShell 에서** (절대 경로 사용 권장):

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\Users\USER\apple-cert\certificate.p12")) | Set-Clipboard
```

→ 클립보드에 base64 문자열 (수천 자, `MIIK...` 로 시작) 복사됨.

**검증**:
```powershell
(Get-Clipboard).Length
```
→ 4000~6000 사이면 정상.

또는 메모장 열어서 `Ctrl+V` → 긴 문자열 보이는지 확인.

### A-6. App-specific password 생성 (공증용)

공증(notarize) 작업이 사용자 Apple ID 로 인증 요청을 하는데, 일반 비밀번호 대신 **앱 전용 비밀번호** 사용.

1. https://appleid.apple.com/sign-in 로그인
2. 좌측 메뉴 **Sign-In and Security** → **App-Specific Passwords**
3. **+ Generate Password** → 이름: `GitHub Actions Notarization` (식별용, 자유롭게)
4. 표시되는 비밀번호 (`xxxx-xxxx-xxxx-xxxx` 형식) **즉시 복사 + 메모**
   - ⚠️ **한 번만 보여줌**, 닫으면 다시 못 봄

### A-7. Team ID 확인

1. https://developer.apple.com/account 접속
2. **Membership** 섹션 (또는 **Membership details**)
3. **Team ID** (10자 영숫자, 예: `ABCD123456`) 복사

---

## Phase B. GitHub Secrets 등록

1. GitHub repo 페이지 → **Settings** 탭 → 좌측 **Secrets and variables** → **Actions**
   - 직접 URL: `https://github.com/<owner>/<repo>/settings/secrets/actions`
2. **New repository secret** 클릭하고 아래 6개를 차례로 등록:

| Secret 이름 | 값 어디서? |
|---|---|
| `APPLE_CERTIFICATE_P12_BASE64` | A-5 의 base64 문자열 (클립보드) |
| `APPLE_CERTIFICATE_PASSWORD` | A-4 에서 입력한 export password |
| `APPLE_ID` | A-6 로그인한 Apple ID 이메일 |
| `APPLE_APP_SPECIFIC_PASSWORD` | A-6 의 `xxxx-xxxx-xxxx-xxxx` |
| `APPLE_TEAM_ID` | A-7 의 10자 ID (예: `ABCD123456`) |
| `KEYCHAIN_PASSWORD` | 본인이 정한 강한 비밀번호 (예: `BinaveOCR2026!CI`) |

> 💡 Secret 값은 **저장 후 다시 못 봄**. 입력 시 신중하게.

---

## Phase C. 빌드 인프라 코드

이미 이 repo 에 있다면 스킵. 새 프로젝트에 처음 적용한다면 다음 5개 파일을 만들고 push 하세요.

### C-1. `build/build_mac.spec` — PyInstaller 스펙

macOS .app 번들 생성 설정. 주요 차이점 (Windows spec 대비):
- Playwright 캐시 위치: `~/Library/Caches/ms-playwright`
- `BUNDLE()` 블록으로 .app 패키징
- `info_plist` 에 권한 사유 + 번들 식별자
- macOS 전용 hidden imports: `pynput.keyboard._darwin` 등

(전체 내용은 이 repo 의 `build/build_mac.spec` 참조)

### C-2. `build/entitlements.plist` — Hardened Runtime 권한

PyInstaller로 만든 Python 앱이 Apple 의 hardened runtime + 공증을 통과하려면 다음 권한 필수:

```xml
<key>com.apple.security.cs.allow-dyld-environment-variables</key><true/>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
<key>com.apple.security.cs.disable-library-validation</key><true/>
<key>com.apple.security.cs.allow-jit</key><true/>
<key>com.apple.security.network.client</key><true/>
```

(전체는 `build/entitlements.plist` 참조)

이 권한들 없으면 codesign 은 통과해도 **공증 후 실행 시 dyld error 발생**.

### C-3. `build/rthook_set_paths.py` — 런타임 훅

OS 독립적 (Windows + macOS 공용). PyInstaller frozen 환경에서:
- 번들된 PaddleOCR/EasyOCR 모델을 `~/.paddlex` / `~/.EasyOCR` 로 시드
- Playwright 는 `PLAYWRIGHT_BROWSERS_PATH` 환경변수로 가리킴

### C-4. `scripts/prepare_models.py` — 모델 사전 다운로드

CI 러너는 깨끗한 상태로 시작 → PaddleOCR/EasyOCR 모델이 캐시에 없음 → PyInstaller가 빈 캐시 번들. 빌드 직전 이 스크립트로 모델 다운받아 캐시에 저장.

### C-5. `.github/workflows/build-mac.yml` — GitHub Actions 워크플로우

핵심 흐름:

```yaml
on:
  workflow_dispatch:        # 수동 트리거
  push:
    tags: ['v*']            # 태그 push 시 자동

jobs:
  build:
    runs-on: macos-latest   # ARM64 (Apple Silicon)
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r requirements-build.txt
      - playwright install chromium
      - python scripts/prepare_models.py    # 모델 사전 다운
      - pyinstaller build/build_mac.spec    # .app 빌드
      - import certificate to keychain      # Secret 에서 인증서 import
      - codesign --deep --options runtime   # 깊은 서명
      - create-dmg                          # DMG 패키징
      - xcrun notarytool submit --wait      # Apple 공증
      - xcrun stapler staple                # 공증 결과 박기
      - upload-artifact                     # 다운로드용
      - softprops/action-gh-release         # 태그면 Release 첨부
```

### C-6. `.gitignore` 수정

`build/` 안의 `*.plist` 도 git 추적하도록:

```diff
 /build/*
 !/build/*.spec
 !/build/*.py
+!/build/*.plist
 /dist/
```

### C-7. Commit + Push

```bash
git add .github/workflows/build-mac.yml \
        build/build_mac.spec \
        build/entitlements.plist \
        scripts/prepare_models.py \
        .gitignore
git commit -m "Add macOS build infrastructure"
git push origin main
```

---

## Phase D. 첫 빌드 트리거

### D-1. 워크플로우 수동 실행

1. https://github.com/`<owner>`/`<repo>`/actions 접속
2. 좌측 워크플로우 목록 → **Build macOS** 클릭
3. 우측 상단 **Run workflow** 드롭다운 → Branch: `main` → **Run workflow** 버튼

→ 1-2초 후 새 run 이 목록 맨 위에 노란색 ⏵ 아이콘으로 등장.

### D-2. 진행 모니터링

진행 중인 run 클릭 → **build** 잡 클릭 → 단계별 로그 실시간 확인.

| 단계 | 예상 시간 | 무엇을 보면 OK? |
|---|---|---|
| Checkout / Setup Python | ~30초 | 초록 ✓ |
| Install dependencies | ~3-5분 | 마지막에 `Successfully installed ...` |
| Playwright install | ~1-2분 | `chromium-XXXX downloaded` |
| **Download OCR models** | **~3-5분** | `✓ Models ready for bundling.` |
| **PyInstaller build** | **~10-15분** | `Building COLLECT ... completed successfully.` |
| Import signing certificate | ~10초 | `Developer ID Application: ...` 표시 |
| Codesign | ~30초 | `valid on disk` |
| Create DMG | ~1-2분 | `installer/dist/BinaveOCR-X.X.X.dmg` |
| **Notarize** | **~2-10분** | `status: Accepted` (가장 변동 큼) |
| Upload artifact | ~30초 | 마지막 단계 |

전체 약 **20-30분** 소요.

### D-3. 산출물 다운로드

빌드 성공 시 (모든 단계 ✓):

1. 같은 run 페이지 하단으로 스크롤 → **Artifacts** 섹션
2. `BinaveOCR-mac-X.X.X` 항목 클릭 → `.zip` 다운로드
3. 압축 해제 → `BinaveOCR-X.X.X.dmg`

---

## Phase E. 친구/베타 테스터에게 전달

### E-1. DMG 전달

USB / AirDrop / Google Drive / GitHub Release 등 편한 방법으로 친구의 Mac 에 전달.

### E-2. 친구의 설치 절차 (안내문 템플릿)

> **Binave OCR 설치 안내**
>
> 1. 받은 `BinaveOCR-0.2.0.dmg` 파일을 더블클릭하면 창이 열립니다.
> 2. 안에 보이는 **"Binave OCR" 앱 아이콘**을 **Applications 폴더**로 드래그하세요.
> 3. Applications 폴더에서 **Binave OCR** 더블클릭으로 실행.
> 4. 첫 실행 시 macOS 가 권한을 요청합니다. **모두 허용**해 주세요:
>    - 화면 녹화 (스크린샷 OCR 용)
>    - 입력 모니터링 (글로벌 단축키 용)
>    - 시스템 설정 → 개인정보 보호 및 보안 → 각 항목 토글 ON
> 5. 권한 토글 후 **앱을 종료하고 다시 실행** (권한이 적용됨).

### E-3. 검증 체크리스트

친구에게 확인 부탁할 항목:

- [ ] DMG 마운트 시 경고 없음 (공증 OK)
- [ ] Applications 드래그 후 실행 시 "확인되지 않은 개발자" 경고 **없음** (공증 OK)
- [ ] 트레이 아이콘 정상 표시
- [ ] 단축키 동작 (`Cmd+Shift+1/2/3`)
- [ ] 전체화면 OCR / 구역 OCR / 웹페이지 OCR 동작
- [ ] 결과창 + 번역 + 히스토리 정상
- [ ] 헤더 ⚙ 톱니 → 설정 다이얼로그 (API 키 입력 필요 시 안내)

---

## 부록: 트러블슈팅

### 빌드 자체가 실패할 때

| 단계 빨강 | 원인 후보 | 해결 |
|---|---|---|
| Install dependencies | requirements 충돌 | 로그의 마지막 ERROR 라인 확인. PyInstaller 버전 호환성 문제일 수 있음. |
| Download OCR models | 네트워크 / 모델 서버 일시 장애 | 워크플로우 재실행 (대부분 OK) |
| PyInstaller build | hidden imports 누락 / 모듈 못 찾음 | 로그에서 `ModuleNotFoundError` 또는 `ImportError` 검색 → spec 의 `hiddenimports` 에 추가 |
| Import signing certificate | `APPLE_CERTIFICATE_P12_BASE64` 잘못 | base64 문자열에 줄바꿈/공백 섞여있는지 확인. 다시 인코딩 후 secret 갱신 |
| Codesign | `find-identity` 결과가 비었음 | .p12 가 잘못됐거나 password 가 안 맞음 → A-4, A-5 다시 |
| Notarize | "Invalid credentials" / "Authentication failed" | `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD` / `APPLE_TEAM_ID` 중 하나 잘못. 셋 다 다시 확인 |
| Notarize | "Submitted but rejected" | 공증 거절. 로그 다운로드해서 사유 확인 (보통 entitlements 부족 / 서명 누락 파일) |

### 친구 Mac 에서 발생하는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| "확인되지 않은 개발자" 경고 | 공증 안 됨 또는 stapling 누락 | workflow 의 notarize 단계 로그 확인. staple 안 되면 stapler validate 통과 안 함 |
| "이 앱은 손상되었습니다" | DMG 가 staple 안 된 상태로 다운로드 후 macOS 가 인터넷 검증 시도했는데 timing 문제 | DMG 우클릭 → 열기 → "그래도 열기" |
| 권한 다이얼로그 안 뜸 | macOS 시스템 설정 → 개인정보 보호 및 보안에서 직접 추가 | 시스템 설정 → 개인정보 보호 및 보안 → 화면 녹화 / 입력 모니터링 → +로 앱 추가 |
| OCR 안 됨 (PaddleOCR 로딩 실패) | 번들된 모델 시드 실패 | `~/Library/Logs/Binave OCR/` 또는 앱 내부 logs 확인. 시드 실패 시 첫 실행에서 자동 다운로드되므로 인터넷 연결 필요 |

### 빌드는 OK 인데 실제로 잘 동작하는지 확실치 않을 때

GitHub Actions Run 페이지에서 **"build" job 의 모든 단계가 초록 ✓ 이고**, **artifact 가 생성됐다면** 코드사인 + 공증은 통과한 상태입니다. 실 동작은 친구 검증으로만 확인 가능.

---

## 부록: 향후 운영

### 다음 빌드부터

1. **코드 변경 → push** (main 또는 PR)
2. 자동 빌드를 원하면 **태그 push**:
   ```bash
   git tag v0.2.1
   git push origin v0.2.1
   ```
3. 워크플로우가 자동 실행 → DMG 빌드 → **GitHub Release 에 draft 로 첨부**
4. Release 페이지에서 publish → 사용자들이 다운로드

### 버전 번호 동기화 (Windows + macOS)

3 곳을 같은 버전으로 유지:
- `src/__init__.py` 의 `__version__`
- `installer/binave_ocr.iss` 의 `MyAppVersion` (Windows)
- (필요 시) `build/build_mac.spec` 의 `info_plist` 안 `CFBundleVersion` / `CFBundleShortVersionString`

자동화하고 싶으면 `bumpver` Python 패키지 등으로 한 번에 갱신 가능.

### 인증서 갱신

- **Developer ID Application 인증서**: 5년 유효
- 만료 전에 같은 절차로 재발급 후 GitHub Secret `APPLE_CERTIFICATE_P12_BASE64` 갱신

### Apple Silicon vs Intel

`runs-on: macos-latest` 는 2024년부터 **Apple Silicon (arm64)**. Intel Mac 사용자도 지원하려면:
- Universal Binary 빌드 (PyInstaller 가 `target_arch='universal2'` 옵션 지원하지만 numpy/torch 등이 모두 universal 휠 필요)
- 또는 별도 잡으로 `runs-on: macos-13` (Intel) 추가해서 두 산출물 만들기

대부분의 신규 Mac (2020+) 은 Apple Silicon 이므로 첫 배포는 arm64 만으로도 충분.

### 비용 모니터링

- Public repo: GitHub Actions 무료
- Private repo: macos-latest 분당 $0.08 → 25분 빌드 = ~$2/회
  - 한 달에 빌드 10회 = ~$20
  - GitHub 계정 무료 제공량 (Free: 2000분/월, Pro: 3000분/월) 일부 차감

Apple Developer Program: $99/년 — 자동 갱신.

### 다음 단계 옵션

- **Sparkle 자동 업데이트**: 사용자가 앱 안에서 새 버전 설치 (별도 셋업 필요)
- **Mac App Store 배포**: 별도 인증서 (Mac App Store distribution) + 샌드박싱 + Apple 심사 (전혀 다른 트랙)
- **Universal Binary**: Intel + ARM 둘 다 동시 지원

---

## 마무리 — 한 페이지 체크리스트

```
[ ] Apple Developer Program 가입 ($99/년)
[ ] OpenSSL (Git for Windows) 사용 가능

[ ] 비밀키 + CSR 생성 (openssl genrsa / req)
[ ] Apple Developer 콘솔에서 Developer ID Application 인증서 발급
[ ] .cer + 비밀키 → .p12 합치기 (export password 메모)
[ ] .p12 → base64 인코딩
[ ] App-Specific Password 생성 (xxxx-xxxx-xxxx-xxxx 메모)
[ ] Team ID 확인

[ ] GitHub Secrets 6개 등록
    [ ] APPLE_CERTIFICATE_P12_BASE64
    [ ] APPLE_CERTIFICATE_PASSWORD
    [ ] APPLE_ID
    [ ] APPLE_APP_SPECIFIC_PASSWORD
    [ ] APPLE_TEAM_ID
    [ ] KEYCHAIN_PASSWORD

[ ] 빌드 인프라 5개 파일
    [ ] .github/workflows/build-mac.yml
    [ ] build/build_mac.spec
    [ ] build/entitlements.plist
    [ ] build/rthook_set_paths.py (cross-platform)
    [ ] scripts/prepare_models.py
    [ ] .gitignore 에 !/build/*.plist 추가

[ ] git commit + push

[ ] GitHub Actions → Build macOS → Run workflow
[ ] 빌드 모니터링 (~25분)
[ ] Artifact 다운로드 (DMG)
[ ] 친구 Mac 에서 검증
[ ] (선택) GitHub Release 에 첨부 + 공개
```

---

> **이 가이드는 Binave OCR v0.2.0 첫 macOS 빌드 셋업 (2026-05) 작업을 기반으로 작성되었습니다.**

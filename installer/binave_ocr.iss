; Binave OCR — Windows Installer (Inno Setup 6 script)
;
; 빌드:
;   1) https://jrsoftware.org/isdl.php 에서 Inno Setup 6 설치
;      (또는 PowerShell 관리자: winget install JRSoftware.InnoSetup)
;   2) 먼저 PyInstaller 빌드:
;        pyinstaller build/build_windows.spec --clean --noconfirm --workpath build/_pyi_work
;   3) 다음 중 하나로 설치파일 생성:
;        a) Inno Setup 컴파일러로 이 .iss 파일 열고 Build > Compile
;        b) CLI:  & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\binave_ocr.iss
;
; 산출물: installer\dist\BinaveOCR-Setup-0.1.0.exe (예상 약 1GB)

#define MyAppName       "Binave OCR"
#define MyAppShortName  "BinaveOCR"
#define MyAppVersion    "0.2.0"
#define MyAppPublisher  "Binave"
#define MyAppExeName    "BinaveOCR.exe"
#define MyAppSourceDir  "..\dist\BinaveOCR"

[Setup]
; AppId 는 절대 변경하지 마세요. Windows 가 같은 앱(업그레이드 vs 신규)을 식별하는 키입니다.
AppId={{9A35EC33-1415-486A-ADC8-1D98EE971D49}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppSupportURL=https://github.com/jay-twiggy/OCR
DefaultDirName={userpf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
OutputDir=dist
OutputBaseFilename=BinaveOCR-Setup-{#MyAppVersion}
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 관리자 권한 없이 사용자 폴더에 설치 (UAC prompt 회피)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; 산출물이 크므로 디스크 공간 검사 비활성 (PyInstaller dist 그대로 압축)
DiskSpanning=no
; 한국어 기본
ShowLanguageDialog=auto

[Languages]
Name: "korean";  MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenu";   Description: "시작 메뉴에 바로가기 추가";       GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart";   Description: "Windows 시작 시 자동 실행 (트레이 상주)"; GroupDescription: "기타:"; Flags: unchecked

[Files]
; PyInstaller 산출물 전체 (BinaveOCR.exe + _internal/ + _bundled/...)
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";          Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}";    Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[Registry]
; "Windows 시작 시 자동 실행" Tasks 선택 시 HKCU\...\Run 에 등록 (사용자 단위, 관리자 권한 불필요)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppShortName}"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 설치 폴더 안에 런타임에 생긴 로그/캡처 폴더 정리
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\_internal\logs"
; ~/.paddlex, ~/.EasyOCR 사용자 홈 캐시는 보존
; (다른 앱이 공유할 수 있고, 다음 설치 시 시드 비용 절감)

; GameTools TES — NSIS Installer Script
; Requires NSIS 3.x (https://nsis.sourceforge.io/Download)
; Called by build_windows.ps1 with /DVERSION=x.y.z /DSRC_EXE=... /DOUT_DIR=...
;
; What this installer does:
;   - Installs GameToolsTES.exe to %ProgramFiles%\GameTools TES\
;   - Creates a Start Menu shortcut
;   - Optionally creates a Desktop shortcut
;   - Registers the application in Programs and Features (Add/Remove Programs)
;   - Creates an uninstaller (also registered in the registry)
;   - Allows clean removal via uninstaller or Programs and Features

Unicode true
SetCompressor /SOLID lzma

; ── Variables passed from build script ───────────────────────────────────────
!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef SRC_EXE
  !define SRC_EXE "GameToolsTES.exe"
!endif
!ifndef OUT_DIR
  !define OUT_DIR "."
!endif

; ── Installer metadata ────────────────────────────────────────────────────────
Name "GameTools — The Elder Scrolls"
OutFile "${OUT_DIR}\GameTools_TES_Setup_${VERSION}.exe"
InstallDir "$PROGRAMFILES64\GameTools TES"
InstallDirRegKey HKLM "Software\GameTools\TES" "InstallDir"
RequestExecutionLevel admin
ShowInstDetails show

; ── Branding ──────────────────────────────────────────────────────────────────
BrandingText "GameTools TES v${VERSION}"
Caption "GameTools TES v${VERSION} Setup"

; ── Registry key for Programs and Features ────────────────────────────────────
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\GameToolsTES"
!define APP_KEY       "Software\GameTools\TES"

; ── Pages ─────────────────────────────────────────────────────────────────────
Page license
Page directory
Page components
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

LicenseData "${__FILEDIR__}\..\..\..\..\LICENSE.txt"

; ── Sections ──────────────────────────────────────────────────────────────────

Section "GameTools TES (required)" SecMain
  SectionIn RO   ; required, cannot be unchecked

  SetOutPath "$INSTDIR"
  File "${SRC_EXE}"

  ; ── Write application registry key ──────────────────────────────────────
  WriteRegStr HKLM "${APP_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${APP_KEY}" "Version"    "${VERSION}"

  ; ── Register in Programs and Features ───────────────────────────────────
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"          "GameTools — The Elder Scrolls"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"       "${VERSION}"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"            "GameTools Project"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"      '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${UNINSTALL_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"             1
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"             1

  ; ── Estimate installed size (in KB) ─────────────────────────────────────
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

  ; ── Create uninstaller ───────────────────────────────────────────────────
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; ── Start Menu shortcut ──────────────────────────────────────────────────
  CreateDirectory "$SMPROGRAMS\GameTools TES"
  CreateShortcut  "$SMPROGRAMS\GameTools TES\GameTools TES.lnk" \
                  "$INSTDIR\GameToolsTES.exe" "" "$INSTDIR\GameToolsTES.exe" 0 \
                  SW_SHOWNORMAL "" "GameTools — The Elder Scrolls Crafting Assistant"

SectionEnd


Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\GameTools TES.lnk" \
                 "$INSTDIR\GameToolsTES.exe" "" "$INSTDIR\GameToolsTES.exe" 0
SectionEnd


; ── Uninstaller ───────────────────────────────────────────────────────────────

Section "Uninstall"
  ; Remove files
  Delete "$INSTDIR\GameToolsTES.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir  "$INSTDIR"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\GameTools TES\GameTools TES.lnk"
  RMDir  "$SMPROGRAMS\GameTools TES"
  Delete "$DESKTOP\GameTools TES.lnk"

  ; Remove registry entries
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "${APP_KEY}"
  DeleteRegKey /ifempty HKLM "Software\GameTools"
SectionEnd


; ── Descriptions ─────────────────────────────────────────────────────────────
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}    "The GameTools TES application. Required."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Add a shortcut to the Desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

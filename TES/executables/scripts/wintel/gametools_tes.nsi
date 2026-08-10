; GameTools TES — NSIS Installer Script
; Requires NSIS 3.x (https://nsis.sourceforge.io/Download)
; Called by build_windows.ps1 (or CI) with:
;   /DVERSION=x.y.z  /DSRC_DIR=<abs-path-to-standalone-dist-dir>  /DOUT_DIR=<abs-path>
;
; What this installer does:
;   - Copies the entire Nuitka standalone directory to %ProgramFiles%\GameTools TES\
;   - Creates a Start Menu shortcut
;   - Optionally creates a Desktop shortcut
;   - Registers the application in Programs and Features (Add/Remove Programs)
;   - Creates an uninstaller (also registered in the registry)
;   - Supports in-place upgrade: re-run the installer to update without uninstalling first
;   - Allows clean removal via uninstaller or Programs and Features

Unicode true
SetCompressor /SOLID lzma

!include "FileFunc.nsh"   ; needed for ${GetSize}

; ── Variables passed from build script ───────────────────────────────────────
!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef SRC_DIR
  !define SRC_DIR "GameToolsTES.dist"
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

  ; Copy the entire Nuitka standalone directory (exe + DLLs + data subdirs).
  ; File /r with a trailing \* copies the CONTENTS (not the dir itself) into
  ; $INSTDIR.  If upgrading, existing files are overwritten in place — the user
  ; does not need to uninstall first.
  File /r "${SRC_DIR}\*"

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
  ; Remove shortcuts
  Delete "$SMPROGRAMS\GameTools TES\GameTools TES.lnk"
  RMDir  "$SMPROGRAMS\GameTools TES"
  Delete "$DESKTOP\GameTools TES.lnk"

  ; Remove registry entries
  DeleteRegKey HKLM "${UNINSTALL_KEY}"
  DeleteRegKey HKLM "${APP_KEY}"
  DeleteRegKey /ifempty HKLM "Software\GameTools"

  ; Remove all installed files.  /REBOOTOK schedules the uninstaller exe itself
  ; for deletion on next reboot if it cannot be deleted immediately (it is the
  ; running process).  All other files are removed immediately.
  RMDir /r /REBOOTOK "$INSTDIR"
SectionEnd

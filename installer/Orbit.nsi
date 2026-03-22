; Orbit NSIS Installer Script
; Requires NSIS 3.x — https://nsis.sourceforge.io/

!include "MUI2.nsh"
!include "LogicLib.nsh"

;--------------------------------
; General
Name "Orbit"
OutFile "..\dist\Orbit-Setup.exe"
InstallDir "$PROGRAMFILES64\Orbit"
InstallDirRegKey HKLM "Software\Orbit" "Install_Dir"
RequestExecutionLevel admin
Unicode True

;--------------------------------
; Version info
VIProductVersion "0.1.0.0"
VIAddVersionKey "ProductName"     "Orbit"
VIAddVersionKey "ProductVersion"  "0.1.0"
VIAddVersionKey "FileDescription" "Orbit Installer"
VIAddVersionKey "LegalCopyright"  "2024 Orbit"

;--------------------------------
; Interface
!define MUI_ABORTWARNING
!define MUI_ICON "..\pyside-app\resources\icon.ico"
!define MUI_UNICON "..\pyside-app\resources\icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "PortugueseBR"

;--------------------------------
; Installer sections
Section "Orbit" SecMain
    SectionIn RO
    SetOutPath "$INSTDIR"
    File /r "..\pyside-app\dist\Orbit\*.*"

    ; Write registry
    WriteRegStr HKLM "Software\Orbit" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit" \
        "DisplayName" "Orbit"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit" \
        "DisplayVersion" "0.1.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit" \
        "Publisher" "Orbit"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit" \
        "NoRepair" 1

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Start menu shortcut
    CreateDirectory "$SMPROGRAMS\Orbit"
    CreateShortcut "$SMPROGRAMS\Orbit\Orbit.lnk" "$INSTDIR\Orbit.exe" \
        "" "$INSTDIR\Orbit.exe" 0
    CreateShortcut "$SMPROGRAMS\Orbit\Desinstalar Orbit.lnk" "$INSTDIR\Uninstall.exe"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\Orbit.lnk" "$INSTDIR\Orbit.exe" \
        "" "$INSTDIR\Orbit.exe" 0
SectionEnd

;--------------------------------
; Uninstaller section
Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\Orbit\*.*"
    RMDir "$SMPROGRAMS\Orbit"
    Delete "$DESKTOP\Orbit.lnk"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Orbit"
    DeleteRegKey HKLM "Software\Orbit"

    ; Remove startup entry if set
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Orbit"
SectionEnd

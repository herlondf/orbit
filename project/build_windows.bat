@echo off
REM Build OctoChat Windows binaries using Tauri (run this on Windows directly)
REM Prerequisites: Node.js/npm, Rust stable-msvc, Microsoft C++ Build Tools, WebView2
REM Usage: build_windows.bat [--skip-install]

setlocal enabledelayedexpansion

set SKIP_INSTALL=0
if /I "%1"=="--skip-install" set SKIP_INSTALL=1

echo === OctoChat Windows Build ===

REM Check Node.js and npm
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install Node.js and add it to PATH.
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Install Node.js/npm and add it to PATH.
    exit /b 1
)

REM Load MSVC environment
set VS_DEV_CMD=
if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" (
    set "VS_DEV_CMD=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat"
)
if not defined VS_DEV_CMD if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" (
    set "VS_DEV_CMD=C:\Program Files\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"
)

if not defined VS_DEV_CMD (
    echo ERROR: VsDevCmd.bat not found. Install Microsoft C++ Build Tools or Visual Studio 2022.
    exit /b 1
)

call "%VS_DEV_CMD%"
if errorlevel 1 (
    echo ERROR: Failed to initialize MSVC environment.
    exit /b 1
)

set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

REM Check Rust toolchain
cargo --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: cargo not found. Install Rust stable-msvc for the current user.
    exit /b 1
)

rustc --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: rustc not found. Install Rust stable-msvc for the current user.
    exit /b 1
)

REM Install/update JS dependencies
if "%SKIP_INSTALL%"=="0" (
    echo =^> Installing npm dependencies...
    npm install
    if errorlevel 1 (
        echo ERROR: npm install failed.
        exit /b 1
    )
)

REM Build Tauri bundle
echo =^> Building OctoChat with Tauri...
call npm run tauri:build
if errorlevel 1 (
    echo ERROR: Tauri build failed.
    exit /b 1
)

echo =^> Done!
if exist "src-tauri\target\release\octochat.exe" (
    echo App binary: src-tauri\target\release\octochat.exe
)
if exist "src-tauri\target\release\bundle" (
    echo Bundles: src-tauri\target\release\bundle
    dir /b "src-tauri\target\release\bundle"
)

endlocal

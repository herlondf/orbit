@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  Orbit MSIX Builder
echo ============================================

:: Check for PyInstaller
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found. Run: pip install pyinstaller
    exit /b 1
)

set DIST_DIR=%~dp0..\dist
set BUILD_DIR=%~dp0..\build
set PKG_DIR=%~dp0

:: Step 1: Build with PyInstaller
echo [1/4] Building executable with PyInstaller...
cd /d %~dp0..
pyinstaller --clean Orbit.spec
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

:: Step 2: Prepare MSIX staging folder
echo [2/4] Preparing MSIX staging folder...
set STAGING=%BUILD_DIR%\msix_staging
if exist "%STAGING%" rd /s /q "%STAGING%"
mkdir "%STAGING%\Orbit"
mkdir "%STAGING%\Assets"

xcopy /s /e /q "%DIST_DIR%\Orbit\*" "%STAGING%\Orbit\"
copy "%PKG_DIR%\AppxManifest.xml" "%STAGING%\"
copy "%PKG_DIR%\Assets\*" "%STAGING%\Assets\"

:: Step 3: Create MSIX package
echo [3/4] Creating MSIX package...
set MSIX_OUT=%DIST_DIR%\Orbit.msix
if exist "%MSIX_OUT%" del "%MSIX_OUT%"

makeappx pack /d "%STAGING%" /p "%MSIX_OUT%" /nv
if %errorlevel% neq 0 (
    echo [WARNING] makeappx failed. Is Windows SDK installed?
    echo Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
    goto :inno
)

:: Step 4: Self-sign for testing (optional)
echo [4/4] Self-signing package (for testing only)...
if exist "%PKG_DIR%\Orbit_test.pfx" (
    signtool sign /fd SHA256 /a /f "%PKG_DIR%\Orbit_test.pfx" /p Orbit "%MSIX_OUT%"
    echo [OK] Signed: %MSIX_OUT%
) else (
    echo [INFO] No PFX found. Package unsigned (add Orbit_test.pfx to sign).
    echo [OK] MSIX created (unsigned): %MSIX_OUT%
)

:inno
echo.
echo ============================================
echo  Building Inno Setup Installer
echo ============================================
where iscc >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Inno Setup not found, skipping .exe installer
    echo Download from: https://jrsoftware.org/isdl.php
    goto :done
)

iscc "%PKG_DIR%\Orbit_Setup.iss"
if %errorlevel% equ 0 (
    echo [OK] Inno Setup installer created
) else (
    echo [ERROR] Inno Setup build failed
)

:done
echo.
echo Done! Check dist\ folder for output files.
endlocal

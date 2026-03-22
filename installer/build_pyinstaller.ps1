# Orbit — PyInstaller build script
# Run from repo root: powershell -File installer/build_pyinstaller.ps1

param([switch]$OneFile)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ╔══════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     Orbit — PyInstaller Build    ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $repoRoot "pyside-app"
Set-Location $repoRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { Write-Error "Python not found in PATH"; exit 1 }

Write-Host "[1/4] Installing dependencies..." -ForegroundColor Yellow
pip install -r "$appDir\requirements.txt" pyinstaller cryptography --quiet

$iconArg = @()
$iconPath = Join-Path $appDir "assets\icon.ico"
if (Test-Path $iconPath) {
    $iconArg = @("--icon=$iconPath")
    Write-Host "       Icon: $iconPath"
}

$modeArg = if ($OneFile) { "--onefile" } else { "--onedir" }

Write-Host "[2/4] Running PyInstaller ($modeArg)..." -ForegroundColor Yellow
$buildArgs = @(
    "--noconfirm",
    $modeArg,
    "--name", "Orbit",
    "--noconsole",
    "--workpath", "$repoRoot\build",
    "--distpath", "$repoRoot\dist",
    "--add-data", "$appDir\assets;assets",
    "--add-data", "$appDir\resources;resources",
    "--hidden-import", "PySide6.QtSvg",
    "--hidden-import", "PySide6.QtSvgWidgets",
    "--hidden-import", "PySide6.QtWebEngineCore",
    "--hidden-import", "PySide6.QtWebEngineWidgets",
    "--hidden-import", "PySide6.QtMultimedia",
    "--hidden-import", "cryptography",
    "--hidden-import", "cryptography.hazmat.primitives.ciphers.aead",
    "--hidden-import", "cryptography.hazmat.primitives.kdf.pbkdf2"
) + $iconArg + @("$appDir\main.py")

Set-Location $appDir
pyinstaller @buildArgs

if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build failed"; exit 1 }

Write-Host "[3/4] Build complete!" -ForegroundColor Green
$distPath = Join-Path $repoRoot "dist\Orbit"
Write-Host "       Output: $distPath"

$exePath = Join-Path $distPath "Orbit.exe"
if (Test-Path $exePath) {
    $size = (Get-Item $exePath).Length / 1MB
    Write-Host "       Orbit.exe: $([math]::Round($size, 1)) MB" -ForegroundColor Green
} else {
    Write-Host "       WARNING: Orbit.exe not found" -ForegroundColor Red
}

Write-Host "[4/4] Ready for packaging" -ForegroundColor Cyan

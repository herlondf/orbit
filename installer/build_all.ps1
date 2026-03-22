# Orbit — Build all installers
# Usage: powershell -File installer/build_all.ps1

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     Orbit Installer Builder              ║" -ForegroundColor Cyan
Write-Host "  ║     ZIP + MSI (Win 10) + MSIX (Win 11)  ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptDir
$distDir = Join-Path $repoRoot "dist"

# Step 1: PyInstaller
Write-Host "━━━ Step 1: PyInstaller Build ━━━" -ForegroundColor Magenta
& powershell -File "$scriptDir\build_pyinstaller.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit 1 }

Write-Host ""

# Step 2: ZIP (always works, no extra tools needed)
Write-Host "━━━ Step 2: ZIP Package ━━━" -ForegroundColor Magenta
$zipPath = Join-Path $distDir "Orbit-win-x64.zip"
Compress-Archive -Path "$distDir\Orbit\*" -DestinationPath $zipPath -Force
Write-Host "  ZIP: $zipPath" -ForegroundColor Green

Write-Host ""

# Step 3: MSI
Write-Host "━━━ Step 3: MSI Installer ━━━" -ForegroundColor Magenta
& powershell -File "$scriptDir\build_msi.ps1" -ErrorAction Continue

Write-Host ""

# Step 4: MSIX
Write-Host "━━━ Step 4: MSIX Installer ━━━" -ForegroundColor Magenta
& powershell -File "$scriptDir\build_msix.ps1" -ErrorAction Continue

Write-Host ""
Write-Host "━━━ Build Summary ━━━" -ForegroundColor Green
Write-Host "Output: $distDir"
Write-Host ""
Get-ChildItem "$distDir\Orbit*" -ErrorAction SilentlyContinue | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 1)
    Write-Host "  $($_.Name): ${size} MB" -ForegroundColor White
}
Write-Host ""
Write-Host "Done! ✓" -ForegroundColor Green

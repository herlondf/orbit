# Orbit MSIX Installer Script
# Downloads Orbit-Dev.cer + Orbit-*.msix alongside this script, then run:
#   powershell -ExecutionPolicy Bypass -File install-orbit.ps1
# The script auto-elevates to Administrator if needed.

param(
    [string]$MsixPath = "",
    [string]$CerPath  = ""
)

# ── Auto-elevate to Administrator ─────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")
if (-not $isAdmin) {
    Write-Host "Relaunching as Administrator..." -ForegroundColor Yellow
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`""
    exit
}

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "         Orbit - MSIX Installer           " -ForegroundColor Cyan
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Auto-detect files in same directory as script
if ($MsixPath -eq "") {
    $found = Get-ChildItem $scriptDir -Filter "Orbit-*.msix" | Select-Object -First 1
    if ($found) { $MsixPath = $found.FullName }
}
if ($CerPath -eq "") {
    $found = Get-ChildItem $scriptDir -Filter "Orbit-Dev.cer" | Select-Object -First 1
    if ($found) { $CerPath = $found.FullName }
}

if (-not (Test-Path $MsixPath)) {
    Write-Error "MSIX not found. Place Orbit-*.msix in the same directory as this script."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "MSIX: $MsixPath"

# Import certificate — must go to LocalMachine stores for Add-AppxPackage to trust it
if ($CerPath -and (Test-Path $CerPath)) {
    Write-Host ""
    Write-Host "Step 1/2: Importing developer certificate (LocalMachine)..." -ForegroundColor Yellow
    Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\LocalMachine\Root"         | Out-Null
    Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
    Write-Host "          Certificate imported to Trusted Root + Trusted People." -ForegroundColor Green
} else {
    Write-Host "Step 1/2: Orbit-Dev.cer not found -- skipping cert import." -ForegroundColor Yellow
    Write-Host "          Install may fail. Download Orbit-Dev.cer alongside this script." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2/2: Installing Orbit MSIX package..." -ForegroundColor Yellow
try {
    Add-AppxPackage -Path $MsixPath
    Write-Host ""
    Write-Host "  Orbit installed successfully!" -ForegroundColor Green
    Write-Host "  Find it in the Start Menu." -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host ("  Installation failed: " + $_) -ForegroundColor Red
    Write-Host ""
    Write-Host "  Alternatives:" -ForegroundColor Yellow
    Write-Host '  1. Use the MSI installer: Orbit-*-win-x64.msi  (no cert needed)'
    Write-Host '  2. Use the portable ZIP: Orbit-*-win-x64.zip   (no install needed)'
    Write-Host '  3. Enable Developer Mode: Settings > Privacy & Security > For developers'
}

Write-Host ""
Read-Host "Press Enter to exit"

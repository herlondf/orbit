# Orbit MSIX Installer Script
# Run as Administrator: powershell -ExecutionPolicy Bypass -File install-orbit.ps1
# This script imports the dev certificate and installs the MSIX package.

param(
    [string]$MsixPath = "",
    [string]$CerPath  = ""
)

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
    exit 1
}

Write-Host "MSIX: $MsixPath"

# Import certificate to Trusted Root + Trusted People
if ($CerPath -and (Test-Path $CerPath)) {
    Write-Host ""
    Write-Host "Step 1/2: Importing developer certificate..." -ForegroundColor Yellow
    Write-Host "          This allows Windows to verify the app package signature."
    try {
        $cert = Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\LocalMachine\Root"
        Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
        Write-Host ("          Certificate imported: " + $cert.Subject) -ForegroundColor Green
    } catch {
        Write-Host "          Could not import to LocalMachine (need Admin). Trying CurrentUser..." -ForegroundColor Yellow
        Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
        Import-Certificate -FilePath $CerPath -CertStoreLocation "Cert:\CurrentUser\TrustedPeople" | Out-Null
        Write-Host "          Certificate imported to CurrentUser store." -ForegroundColor Green
    }
} else {
    Write-Host "Step 1/2: No certificate found -- trying unsigned install..." -ForegroundColor Yellow
    Write-Host "          If install fails, enable Developer Mode in Windows Settings." -ForegroundColor Yellow
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
    Write-Host '  1. Enable Developer Mode: Settings > Privacy & Security > For developers'
    Write-Host '  2. Use the MSI installer instead: Orbit-*-win-x64.msi'
    Write-Host '  3. Use the portable ZIP: Orbit-*-win-x64.zip'
}

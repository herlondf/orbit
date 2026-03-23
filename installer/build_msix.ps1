# Orbit — MSIX Installer Builder (Windows 11 compatible)
# Uses makeappx.exe from Windows SDK
# Run from repo root: powershell -File installer/build_msix.ps1

param([string]$DistPath = "")

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ╔══════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     Orbit — MSIX Builder         ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
if ($DistPath -eq "") {
    $distPath = Join-Path $repoRoot "dist\Orbit"
} else {
    $distPath = $DistPath
}
$outputDir = Join-Path $repoRoot "dist"
$msixStagingDir = Join-Path $outputDir "msix_staging"

Write-Host "Repo root : $repoRoot"
Write-Host "Dist path : $distPath"
Write-Host "Output dir: $outputDir"

if (-not (Test-Path (Join-Path $distPath "Orbit.exe"))) {
    Write-Error "dist\Orbit\Orbit.exe not found. Run build_pyinstaller.ps1 first."
    exit 1
}

# ── [1/5] Prepare staging directory ──────────────────────────────────
Write-Host "[1/5] Preparing MSIX staging directory..." -ForegroundColor Yellow
if (Test-Path $msixStagingDir) { Remove-Item -Recurse -Force $msixStagingDir }
New-Item -ItemType Directory -Path $msixStagingDir | Out-Null
Copy-Item -Path "$distPath\*" -Destination $msixStagingDir -Recurse

# ── [2/5] Create AppxManifest.xml ────────────────────────────────────
Write-Host "[2/5] Creating AppxManifest.xml..." -ForegroundColor Yellow

$manifestContent = @"
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  <Identity
    Name="HDX.Orbit"
    Version="1.0.0.0"
    Publisher="CN=HDX Software"
    ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>Orbit</DisplayName>
    <PublisherDisplayName>HDX Software</PublisherDisplayName>
    <Logo>assets\icon_150.png</Logo>
    <Description>Multi-service desktop shell</Description>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily
      Name="Windows.Desktop"
      MinVersion="10.0.17763.0"
      MaxVersionTested="10.0.22621.0" />
  </Dependencies>

  <Resources>
    <Resource Language="en-us" />
    <Resource Language="pt-br" />
  </Resources>

  <Applications>
    <Application
      Id="Orbit"
      Executable="Orbit.exe"
      EntryPoint="Windows.FullTrustApplication">

      <uap:VisualElements
        DisplayName="Orbit"
        Description="Multi-service desktop shell"
        BackgroundColor="#16161a"
        Square150x150Logo="assets\icon_150.png"
        Square44x44Logo="assets\icon_44.png">
        <uap:DefaultTile Wide310x150Logo="assets\icon_310x150.png" />
      </uap:VisualElements>

      <Extensions>
        <!-- orbit:// URL protocol handler -->
        <uap:Extension Category="windows.protocol">
          <uap:Protocol Name="orbit">
            <uap:DisplayName>Orbit Protocol</uap:DisplayName>
          </uap:Protocol>
        </uap:Extension>
      </Extensions>

    </Application>
  </Applications>

  <Capabilities>
    <Capability Name="internetClient" />
    <Capability Name="privateNetworkClientServer" />
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>

</Package>
"@

$manifestContent | Out-File -FilePath (Join-Path $msixStagingDir "AppxManifest.xml") -Encoding UTF8

# ── [3/5] Prepare icons ───────────────────────────────────────────────
Write-Host "[3/5] Preparing icons..." -ForegroundColor Yellow
$msixAssets = Join-Path $msixStagingDir "assets"
if (-not (Test-Path $msixAssets)) { New-Item -ItemType Directory -Path $msixAssets | Out-Null }

$iconSizes = @{
    "icon_44.png"      = 44
    "icon_150.png"     = 150
    "icon_310x150.png" = 310
}

# Minimal valid 1x1 PNG placeholder bytes
$pngPlaceholder = [byte[]]@(
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xD7, 0x63, 0x60, 0x60, 0x60, 0x00,
    0x00, 0x00, 0x04, 0x00, 0x01, 0x27, 0x34, 0x27,
    0x0A, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82
)

foreach ($icon in $iconSizes.Keys) {
    $iconDest = Join-Path $msixAssets $icon
    # Look for icon in pyside-app/assets and project/assets
    $candidates = @(
        (Join-Path $repoRoot "pyside-app\assets\$icon"),
        (Join-Path $repoRoot "project\assets\$icon")
    )
    $found = $false
    foreach ($src in $candidates) {
        if (Test-Path $src) {
            Copy-Item $src $iconDest
            $found = $true
            break
        }
    }
    if (-not $found) {
        Write-Host "       WARNING: $icon not found — using placeholder" -ForegroundColor Yellow
        [System.IO.File]::WriteAllBytes($iconDest, $pngPlaceholder)
    }
}

# ── [4/5] Pack MSIX ──────────────────────────────────────────────────
Write-Host "[4/5] Packaging MSIX..." -ForegroundColor Yellow

$makeappx = $null
$sdkPaths = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe",
    "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\makeappx.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe",
    "C:\Program Files\Windows Kits\10\bin\*\x64\makeappx.exe"
)
foreach ($pattern in $sdkPaths) {
    $found = Get-Item $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { $makeappx = $found.FullName; break }
}

# Also try finding via where.exe (PATH)
if (-not $makeappx) {
    $fromPath = & where.exe makeappx.exe 2>$null | Select-Object -First 1
    if ($fromPath) { $makeappx = $fromPath }
}

$msixOutput = Join-Path $outputDir "Orbit-Setup.msix"

if ($makeappx) {
    Write-Host "       Using: $makeappx"
    & $makeappx pack /d "$msixStagingDir" /p "$msixOutput" /o
} else {
    Write-Error @"
makeappx.exe not found. Install Windows 10/11 SDK:
  winget install Microsoft.WindowsSDK
Or download from: https://developer.microsoft.com/windows/downloads/windows-sdk/
"@
    exit 1
}

if ($LASTEXITCODE -ne 0) { Write-Error "makeappx failed"; exit 1 }

# ── [5/5] Sign + export public cert for end-user trust ───────────────
Write-Host "[5/5] Signing with self-signed certificate..." -ForegroundColor Yellow

$signtool = $null
$signtoolPaths = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
    "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe"
)
foreach ($pattern in $signtoolPaths) {
    $found = Get-Item $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) { $signtool = $found.FullName; break }
}

if ($signtool) {
    $certPath = Join-Path $outputDir "Orbit-Dev.pfx"
    $cerPath  = Join-Path $outputDir "Orbit-Dev.cer"

    Write-Host "       Creating self-signed certificate..."
    $cert = New-SelfSignedCertificate `
        -Type Custom `
        -Subject "CN=HDX Software" `
        -KeyUsage DigitalSignature `
        -FriendlyName "Orbit Dev Certificate" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")

    # Export PFX (private) for signing
    $pwd = ConvertTo-SecureString -String "OrbitDev2024!" -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $certPath -Password $pwd | Out-Null

    # Export CER (public key only) — this is safe to ship with the release
    Export-Certificate -Cert $cert -FilePath $cerPath -Type CERT | Out-Null
    Write-Host "       Certificate PFX: $certPath"
    Write-Host "       Certificate CER: $cerPath (include in release for user trust)"

    & $signtool sign /fd SHA256 /a /f "$certPath" /p "OrbitDev2024!" "$msixOutput"
    Write-Host "       Signed OK" -ForegroundColor Green
} else {
    Write-Host "       signtool.exe not found — MSIX left unsigned" -ForegroundColor Yellow
}

if (Test-Path $msixOutput) {
    $size = (Get-Item $msixOutput).Length / 1MB
    Write-Host ""
    Write-Host "MSIX created successfully!" -ForegroundColor Green
    Write-Host "  Path: $msixOutput"
    Write-Host "  Size: $([math]::Round($size, 1)) MB"
    Write-Host ""
    Write-Host "To install: run install-orbit.ps1 (imports cert + installs MSIX)" -ForegroundColor Cyan
} else {
    Write-Error "MSIX build failed"
    exit 1
}

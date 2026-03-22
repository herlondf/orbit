# Orbit — MSI Installer Builder using WiX v4
# Run from repo root: powershell -File installer/build_msi.ps1

param([string]$Version = "1.0.0")

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ╔══════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     Orbit — WiX MSI Builder      ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$repoRoot = Split-Path -Parent $PSScriptRoot
$distPath = Join-Path $repoRoot "dist\Orbit"
$outputDir = Join-Path $repoRoot "dist"
$installerDir = Join-Path $repoRoot "installer"

if (-not (Test-Path (Join-Path $distPath "Orbit.exe"))) {
    Write-Error "dist\Orbit\Orbit.exe not found. Run build_pyinstaller.ps1 first."
    exit 1
}

# ── [1/4] Ensure WiX v4 ───────────────────────────────────────────────
Write-Host "[1/4] Checking WiX toolset..." -ForegroundColor Yellow
if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
    Write-Host "       Installing WiX v4 (dotnet tool)..."
    dotnet tool install --global wix
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install WiX v4. Ensure .NET SDK is installed."; exit 1 }
}
Write-Host "       WiX: $(wix --version)"

# ── [2/4] Generate Orbit.wxs ─────────────────────────────────────────
Write-Host "[2/4] Writing Orbit.wxs..." -ForegroundColor Yellow

$wxsPath = Join-Path $installerDir "Orbit.wxs"

# Escape distPath for WiX source attribute
$distPathEsc = $distPath -replace '\\', '\\'

$wxsContent = @"
<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Package
    Name="Orbit"
    Manufacturer="HDX Software"
    Version="$Version"
    UpgradeCode="B2C3D4E5-F6A7-8901-BCDE-F01234567891"
    Scope="perUser"
    Description="Orbit — Multi-service desktop shell">

    <MajorUpgrade DowngradeErrorMessage="A newer version of Orbit is already installed." />
    <MediaTemplate EmbedCab="yes" />

    <!-- Installation folder: %LOCALAPPDATA%\Orbit -->
    <StandardDirectory Id="LocalAppDataFolder">
      <Directory Id="INSTALLFOLDER" Name="Orbit" />
    </StandardDirectory>

    <!-- Desktop shortcut -->
    <StandardDirectory Id="DesktopFolder">
      <Component Id="DesktopShortcut" Guid="*">
        <Shortcut Id="DesktopShortcutOrbit" Name="Orbit"
          Target="[INSTALLFOLDER]Orbit.exe"
          WorkingDirectory="INSTALLFOLDER"
          Icon="OrbitIcon" />
        <RemoveFolder Id="RemoveDesktopFolder" On="uninstall" />
        <RegistryValue Root="HKCU" Key="Software\HDX\Orbit"
          Name="DesktopShortcut" Value="1" Type="integer" KeyPath="yes" />
      </Component>
    </StandardDirectory>

    <!-- Start Menu shortcut -->
    <StandardDirectory Id="ProgramMenuFolder">
      <Directory Id="OrbitMenuFolder" Name="Orbit">
        <Component Id="StartMenuShortcut" Guid="*">
          <Shortcut Id="StartMenuShortcutOrbit" Name="Orbit"
            Target="[INSTALLFOLDER]Orbit.exe"
            WorkingDirectory="INSTALLFOLDER"
            Icon="OrbitIcon" />
          <RemoveFolder Id="RemoveOrbitMenuFolder" On="uninstall" />
          <RegistryValue Root="HKCU" Key="Software\HDX\Orbit"
            Name="StartMenuShortcut" Value="1" Type="integer" KeyPath="yes" />
        </Component>
      </Directory>
    </StandardDirectory>

    <!-- orbit:// URL protocol handler -->
    <Component Id="UrlProtocol" Directory="INSTALLFOLDER" Guid="*">
      <RegistryValue Root="HKCU" Key="Software\Classes\orbit"
        Name="" Value="URL:Orbit Protocol" Type="string" KeyPath="yes" />
      <RegistryValue Root="HKCU" Key="Software\Classes\orbit"
        Name="URL Protocol" Value="" Type="string" />
      <RegistryValue Root="HKCU" Key="Software\Classes\orbit\shell\open\command"
        Name="" Value="&quot;[INSTALLFOLDER]Orbit.exe&quot; &quot;%1&quot;" Type="string" />
    </Component>

    <Feature Id="Complete" Title="Orbit" Level="1">
      <ComponentRef Id="DesktopShortcut" />
      <ComponentRef Id="StartMenuShortcut" />
      <ComponentRef Id="UrlProtocol" />
      <ComponentGroupRef Id="DistFiles" />
    </Feature>

    <Icon Id="OrbitIcon" SourceFile="$(var.DistDir)\Orbit.exe" />

  </Package>
</Wix>
"@

$wxsContent | Out-File -FilePath $wxsPath -Encoding UTF8
Write-Host "       Written: $wxsPath"

# ── [3/4] Harvest dist directory ─────────────────────────────────────
Write-Host "[3/4] Harvesting dist files..." -ForegroundColor Yellow
$harvestPath = Join-Path $installerDir "DistFiles.wxs"

wix harvest dir "$distPath" `
    --name DistFiles `
    --var DistDir `
    --directory-ref INSTALLFOLDER `
    --out "$harvestPath" `
    --nologo

if ($LASTEXITCODE -ne 0) {
    Write-Error "WiX harvest failed. Check that WiX v4 is correctly installed."
    exit 1
}
Write-Host "       Harvested: $harvestPath"

# ── [4/4] Build MSI ──────────────────────────────────────────────────
Write-Host "[4/4] Building MSI..." -ForegroundColor Yellow
$msiOutput = Join-Path $outputDir "Orbit-Setup.msi"

wix build "$wxsPath" "$harvestPath" `
    -dDistDir="$distPath" `
    -out "$msiOutput" `
    --nologo

if ($LASTEXITCODE -ne 0) { Write-Error "WiX build failed"; exit 1 }

$size = (Get-Item $msiOutput).Length / 1MB
Write-Host ""
Write-Host "MSI created successfully!" -ForegroundColor Green
Write-Host "  Path: $msiOutput"
Write-Host "  Size: $([math]::Round($size, 1)) MB" -ForegroundColor Green
Write-Host ""
Write-Host "To install: msiexec /i `"$msiOutput`"" -ForegroundColor Cyan
Write-Host "To uninstall: msiexec /x `"$msiOutput`"" -ForegroundColor Cyan

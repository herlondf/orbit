# Orbit Packaging

Build installers for Orbit on Windows.

## Prerequisites

| Tool | Purpose | Download |
|------|---------|---------|
| PyInstaller | Bundle Python app | `pip install pyinstaller` |
| Windows SDK | makeappx + signtool | [Microsoft](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/) |
| Inno Setup | .exe installer | [jrsoftware.org](https://jrsoftware.org/isdl.php) |
| Pillow | Generate MSIX assets | `pip install Pillow` |

## Quick Start

```bat
cd packaging

# 1. Generate MSIX image assets (first time only)
python generate_assets.py

# 2. Build everything (PyInstaller + MSIX + Inno Setup)
build_msix.bat
```

## Output

| File | Type | Notes |
|------|------|-------|
| `dist\Orbit.msix` | Per-user MSIX | No admin required |
| `dist\Orbit_Setup_1.0.0.exe` | Machine-wide EXE | Via Inno Setup |
| `dist\Orbit\` | Unpacked build | PyInstaller output |

## Per-user vs Machine-wide

- **MSIX** (`Orbit.msix`): Installs to user's AppData, no admin needed, auto-updates friendly
- **Inno Setup** (`Orbit_Setup.exe`): Dialog lets user choose per-user or machine-wide

## Code Signing

For distribution, sign with a real certificate:
```bat
signtool sign /fd SHA256 /a /f YourCert.pfx /p YourPassword dist\Orbit.msix
```

For testing, create a self-signed cert:
```bat
create_test_cert.bat
```
Then trust it: run `certmgr.msc` → Trusted People → Import `Orbit_test.pfx`

## orbit:// URL Protocol

The installer registers the `orbit://` URL scheme. Usage:
- `orbit://service/whatsapp` — open WhatsApp
- `orbit://workspace/work` — switch to workspace
- `orbit://open` — bring window to front

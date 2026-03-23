<p align="center">
  <img src="pyside-app/resources/icon.png" alt="Orbit" width="96" />
</p>

<h1 align="center">Orbit</h1>

<p align="center">
  <strong>Multi-service desktop shell — all your apps in one place</strong><br>
  <sub>WhatsApp &bull; Slack &bull; Gmail &bull; Teams &bull; Discord &bull; Notion &bull; 80+ more</sub>
</p>

<p align="center">
  <a href="https://github.com/herlondf/orbit/releases/latest">
    <img src="https://img.shields.io/github/v/release/herlondf/orbit?label=latest&color=7c6af7&logo=github" alt="Latest Release" />
  </a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey?logo=windows&logoColor=0078d4" alt="Windows" />
  <img src="https://img.shields.io/badge/PySide6-Qt6-41cd52?logo=qt" alt="PySide6" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
  <a href="https://github.com/herlondf/orbit/actions/workflows/ci.yml">
    <img src="https://github.com/herlondf/orbit/actions/workflows/ci.yml/badge.svg" alt="CI" />
  </a>
</p>

<p align="center">
  <a href="#why-orbit">Why Orbit?</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#installation">Installation</a> &bull;
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#keyboard-shortcuts">Shortcuts</a> &bull;
  <a href="#building">Building</a>
</p>

---

## Why Orbit?

Rambox, Ferdium, and Franz give you service aggregation — but nothing more. **Orbit** goes further: isolated sessions, AES-256 encryption, an AI sidebar, glassmorphism UI, workspace scheduling, privacy mode, and a Slack compatibility layer ready for post-May 2026.

| | Rambox | Ferdium | Franz | **Orbit** |
|---|:---:|:---:|:---:|:---:|
| Service isolation (separate cookies) | ✅ | ✅ | ✅ | **✅** |
| Per-workspace accent color | ❌ | ❌ | ❌ | **✅** |
| Glassmorphism sidebar | ❌ | ❌ | ❌ | **✅** |
| AES-256 config encryption | ❌ | ❌ | ❌ | **✅** |
| AI Sidebar (ChatGPT / Claude) | ❌ | ❌ | ❌ | **✅** |
| Privacy Mode (blur overlay) | ❌ | ❌ | ❌ | **✅** |
| Workspace scheduler (auto-switch) | ❌ | ❌ | ❌ | **✅** |
| orbit:// URL scheme | ❌ | ❌ | ❌ | **✅** |
| Slack post-2026 compatibility | ❌ | ❌ | ❌ | **✅** |
| Built-in ad blocker | Paid | ✅ | ❌ | **✅** |
| Cloud sync (GitHub Gist) | Paid | ❌ | ❌ | **✅** |
| Ferdium/Rambox importer | ❌ | ✅ | ❌ | **✅** |
| Do Not Disturb with timer | Partial | Partial | ❌ | **✅** |
| 100% free & open source | ❌ | ✅ | ❌ | **✅** |

---

## Features

### 🌐 81 Services, 13 Categories

Messaging · Work · Email · Productivity · Projects · Design · Dev · CRM · Google · Microsoft · AI · Media · Storage

WhatsApp, Telegram, Slack, Microsoft Teams, Discord, Gmail, Google Calendar, Notion, Trello, Linear, Figma, GitHub, Jira, Salesforce, ChatGPT, Claude, YouTube, Dropbox — and [many more](pyside-app/app/catalog.py).

### 🎨 Modern UI / Glassmorphism

- **Glassmorphism sidebar** with gradient depth, accent glow strip, and scan-line texture
- **Per-workspace accent color** — each workspace has its own color identity
- **6 accent palettes**: Iris · Ocean · Sage · Coral · Rose · Gold
- **Dark / Light / System** theme modes
- **Smooth animations**: fade transitions, badge pulse, hover effects
- **Splash screen** on launch with brand identity

### 🔐 Security First

| Feature | Details |
|---------|---------|
| **AES-256-GCM encryption** | Encrypts `workspaces.json` with master password via PBKDF2 (200k iterations) |
| **PIN lock screen** | Auto-locks after configurable inactivity timeout |
| **Privacy Mode** | Full-screen blur overlay hides all web content — `Ctrl+Shift+P` |
| **Incognito mode** | Per-service — no cookies, no session storage |
| **Per-service proxy** | HTTP and SOCKS5 with authentication |

### 🤖 AI Sidebar

Collapsible right panel (`Ctrl+Shift+A`) with your choice of AI assistant:

- **ChatGPT** (chat.openai.com)
- **Claude** (claude.ai)
- **Gemini** (gemini.google.com)
- **Perplexity** (perplexity.ai)

### 📣 Notification Management

- **Do Not Disturb** — 15 min / 1 h / 4 h / until tomorrow
- **Quiet Hours** — scheduled DND with weekday selector
- **Notification history** — last 50 entries with timestamp
- **Per-service sounds** — custom WAV/MP3 per service
- **Tray badge** — total unread count in system tray icon

### ⚡ Productivity

- **Command palette** (`Ctrl+K`) — fuzzy search across all services and accounts
- **Focus Mode** (`Ctrl+B`) — collapse sidebar, full-width content
- **Workspace scheduler** — auto-switch by time + weekday
- **Reading list** — save URLs from any service for later
- **Session time tracking** — weekly stats per service
- **Keyboard shortcuts** (`Ctrl+?`) — full cheatsheet

### ☁️ Sync & Backup

- **Local backup** — ZIP export/import of all workspaces + settings
- **GitHub Gist sync** — cloud backup with your GitHub token
- **Importer** — migrate from Rambox or Ferdium in one click

### 🔗 orbit:// URL Scheme

Deep-link into any service or workspace from browser, scripts, or other apps:

```
orbit://open                        # bring window to front
orbit://service/slack               # switch to Slack
orbit://workspace/trabalho          # switch to "Trabalho" workspace
```

### 📦 Slack Post-May 2026 Ready

Orbit includes a **Slack Electron compatibility bridge** (`app/slack_bridge.py`):

- Mimics Slack Desktop's Electron user-agent string
- Injects `window.process`, `window.require`, `ipcRenderer` Electron globals
- Sends matching `Sec-CH-UA` Client-Hints HTTP headers
- Shows a guided fallback UI if Slack updates its detection

---

## Installation

### From Release (Recommended)

Download the latest installer from [**Releases**](https://github.com/herlondf/orbit/releases):

| File | Platform | Description |
|------|----------|-------------|
| `Orbit-{version}-win-x64.msix` | Windows 11 | Modern installer — auto-update |
| `Orbit-{version}-win-x64.msi` | Windows 10+ | Traditional MSI installer |
| `Orbit-{version}-win-x64.zip` | Any Windows | Portable — unzip and run |

**Requirements:** Windows 10+ (64-bit), no Python needed — all dependencies bundled.

### From Source

```bash
git clone https://github.com/herlondf/orbit.git
cd orbit
pip install -r pyside-app/requirements.txt
python pyside-app/main.py
```

**Requirements:** Python 3.11+, PySide6 ≥ 6.6

---

## Quick Start

1. **Launch Orbit**
2. Click **+ Add Service** in the sidebar (or `Ctrl+Shift+N`)
3. Browse the catalog of 81 services — pick one, give it a name
4. Click the service icon to open it in the embedded browser
5. Log in once — session persists across restarts

### Multiple Accounts

Add the same service multiple times with different accounts. Each gets its own isolated browser profile (separate cookies, localStorage, IndexedDB).

### Workspaces

Create multiple workspaces (e.g., *Work*, *Personal*, *Freelance*) — each with its own set of services and a custom accent color.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Command palette |
| `Ctrl+B` | Focus mode (toggle sidebar) |
| `Ctrl+L` | Lock screen |
| `Ctrl+D` | Toggle Do Not Disturb |
| `Ctrl+?` | Shortcuts cheatsheet |
| `Ctrl+Shift+A` | AI Sidebar |
| `Ctrl+Shift+P` | Privacy Mode |
| `Ctrl+1…9` | Jump to service #N |
| `Alt+\`` | Quick switch to previous service |

---

## Architecture

```
orbit/
├── pyside-app/
│   ├── app/
│   │   ├── window.py          # Main window + OrbitWindow class (~3000 lines)
│   │   ├── catalog.py         # 81 built-in services, 13 categories
│   │   ├── brand_icons.py     # Embedded SVG brand icons (30+ services)
│   │   ├── theme.py           # ColorTokens, dark/light, 6 accents
│   │   ├── dialogs.py         # All dialog windows
│   │   ├── webview.py         # QWebEngineView wrapper, stealth JS
│   │   ├── encryption.py      # AES-256-GCM, PBKDF2, master password
│   │   ├── slack_bridge.py    # Slack Electron compatibility layer
│   │   ├── workspace_schedule.py  # Time-based workspace auto-switch
│   │   ├── reading_list.py    # Save-for-later URLs
│   │   ├── storage.py         # JSON persistence (%APPDATA%\Orbit\)
│   │   ├── updater.py         # Auto-update via GitHub Releases
│   │   └── ...                # 15 more modules
│   ├── tests/                 # 196 tests
│   └── main.py                # Entry point
├── installer/
│   ├── build_all.ps1          # Build everything
│   ├── build_pyinstaller.ps1  # PyInstaller → dist/Orbit/
│   ├── build_msi.ps1          # WiX Toolset v4 → MSI
│   └── build_msix.ps1         # makeappx → MSIX
└── .github/
    └── workflows/
        ├── ci.yml             # Test on every push/PR
        └── release.yml        # Build + publish on git tag
```

---

## Auto-Update

Orbit checks for updates automatically on startup. When a new version is available:

1. A dialog shows the **changelog** for the new version
2. Download with a **progress bar**
3. **One-click install** — launches MSI installer and exits

Manual check: right-click tray icon → **Verificar atualizações**

---

## Building Installers

```powershell
# Prerequisites: Python 3.11+, optionally WiX v4 and Windows SDK

# Build everything (ZIP + MSI + MSIX)
powershell -File installer/build_all.ps1

# Or step by step:
powershell -File installer/build_pyinstaller.ps1   # creates dist/Orbit/
powershell -File installer/build_msi.ps1            # creates dist/Orbit-Setup.msi
powershell -File installer/build_msix.ps1           # creates dist/Orbit-Setup.msix
```

**WiX Toolset** (for MSI): `dotnet tool install --global wix`  
**Windows SDK** (for MSIX): `winget install Microsoft.WindowsSDK`

---

## Contributing

```bash
git clone https://github.com/herlondf/orbit.git
cd orbit
pip install -r pyside-app/requirements.txt
python pyside-app/main.py
cd pyside-app && pytest tests/ -q
```

---

## License

[MIT License](LICENSE) — © 2026 herlondf

---

<p align="center">
  <sub>Built with Python + PySide6 &bull; <a href="https://github.com/herlondf">herlondf</a></sub>
</p>

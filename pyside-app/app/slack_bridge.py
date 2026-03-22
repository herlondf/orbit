"""
slack_bridge.py — Slack compatibility layer for Orbit.

Context: Slack announced it will discontinue the standalone web client
(accessible from browsers at slack.com) in May 2026. The desktop app will
remain the primary client, running on Electron.

Strategy: Mimic the Slack Desktop (Electron) environment so that
app.slack.com continues to function inside our QWebEngineView.

Techniques used:
  1. Electron-style User-Agent string (HTTP header)
  2. JS environment spoofing: window.process, window.require (Electron globals)
  3. Client-Hints headers matching Electron/Chrome
  4. Fallback UI if Slack blocks us after May 2026
"""
from __future__ import annotations

# Slack Desktop (Windows) Electron user-agent — keep in sync with latest release
# Format: "Slack/<app_version> Chrome/<chromium> Electron/<electron>"
SLACK_ELECTRON_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Slack/4.39.95 Chrome/124.0.6367.243 Electron/30.4.0 Safari/537.36'
)

# Chromium version embedded in Slack's Electron (must match UA above)
_SLACK_CHROME_VER = '124'

# JS injected at DocumentCreation to spoof the Electron environment
# Slack's web bundle checks for these globals to decide if it's running
# inside the desktop app vs. a browser.
SLACK_STEALTH_JS = f"""
(function () {{
    'use strict';

    // --- 1. User-Agent Client Hints ---
    try {{
        const brands = [
            {{ brand: 'Chromium',      version: '{_SLACK_CHROME_VER}' }},
            {{ brand: 'Google Chrome', version: '{_SLACK_CHROME_VER}' }},
            {{ brand: 'Not?A_Brand',   version: '99' }}
        ];
        const uaData = {{
            brands,
            mobile: false,
            platform: 'Windows',
            getHighEntropyValues: (hints) => Promise.resolve({{
                architecture: 'x86', bitness: '64',
                brands, mobile: false, model: '',
                platform: 'Windows', platformVersion: '10.0.0',
                uaFullVersion: '{_SLACK_CHROME_VER}.0.0.0'
            }}),
            toJSON: function() {{ return {{ brands: this.brands, mobile: this.mobile, platform: this.platform }}; }}
        }};
        Object.defineProperty(navigator, 'userAgentData', {{ get: () => uaData }});
    }} catch(e) {{}}

    // --- 2. Remove automation flag ---
    try {{
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
    }} catch(e) {{}}

    // --- 3. Electron globals (Slack checks these) ---
    try {{
        if (!window.process) {{
            window.process = {{
                type: 'renderer',
                platform: 'win32',
                versions: {{
                    node: '20.18.1',
                    electron: '30.4.0',
                    chrome: '{_SLACK_CHROME_VER}.0.0.0',
                }},
                env: {{ SLACK_DESKTOP: '1' }},
                argv: [],
                pid: 12345,
            }};
        }}
    }} catch(e) {{}}

    // --- 4. window.require stub (Electron IPC) ---
    try {{
        if (!window.require) {{
            window.require = function(mod) {{
                if (mod === 'electron') {{
                    return {{
                        ipcRenderer: {{
                            on: function() {{}},
                            send: function() {{}},
                            invoke: function() {{ return Promise.resolve(null); }},
                            removeListener: function() {{}},
                        }},
                        remote: null,
                        shell: {{
                            openExternal: function(url) {{
                                window.open(url, '_blank');
                            }}
                        }},
                    }};
                }}
                return {{}};
            }};
        }}
    }} catch(e) {{}}

    // --- 5. Chrome extension runtime ---
    try {{
        if (!window.chrome) window.chrome = {{}};
        if (!window.chrome.runtime) window.chrome.runtime = {{ id: undefined }};
    }} catch(e) {{}}

    // --- 6. Realistic plugins ---
    try {{
        const arr = [1,2,3,4,5];
        arr.__proto__ = PluginArray.prototype;
        Object.defineProperty(navigator, 'plugins', {{ get: () => arr }});
    }} catch(e) {{}}

    // --- 7. Language ---
    try {{
        Object.defineProperty(navigator, 'languages', {{ get: () => ['pt-BR','pt','en-US','en'] }});
    }} catch(e) {{}}
}})();
"""

# Client-Hints HTTP headers for Slack (Electron values)
SLACK_SEC_CH_UA = (
    f'"Chromium";v="{_SLACK_CHROME_VER}", '
    f'"Google Chrome";v="{_SLACK_CHROME_VER}", '
    f'"Not?A_Brand";v="99"'
)

# Best URL for Slack in embedded mode
SLACK_APP_URL = 'https://app.slack.com/'

# Fallback message shown if Slack blocks us after May 2026
SLACK_BLOCKED_OVERLAY_JS = r"""
(function() {
    if (document.getElementById('orbit-slack-fallback')) return;

    // Detect block: redirect to download page or error
    var url = window.location.href;
    var isBlocked = url.includes('/download') ||
                    url.includes('/intl/') ||
                    document.title.toLowerCase().includes('download');
    if (!isBlocked) return;

    var d = document.createElement('div');
    d.id = 'orbit-slack-fallback';
    d.style.cssText = [
        'position:fixed;top:0;left:0;right:0;bottom:0',
        'background:rgba(24,24,36,0.97)',
        'z-index:99999;display:flex;flex-direction:column',
        'align-items:center;justify-content:center',
        'font-family:Segoe UI,sans-serif;color:#e8e8f0;padding:32px',
    ].join(';');
    d.innerHTML = [
        '<div style="font-size:56px;margin-bottom:16px;">💼</div>',
        '<div style="font-size:22px;font-weight:bold;margin-bottom:12px;">Slack — Modo Desktop</div>',
        '<div style="font-size:14px;color:#a0a0c0;text-align:center;max-width:480px;line-height:1.8;margin-bottom:24px;">',
        'O Slack encerrou o cliente web standalone.<br>',
        'O Orbit está tentando usar o modo Electron — ',
        'se esta mensagem aparecer, o Slack atualizou a detecção.<br><br>',
        '<b>Soluções:</b><br>',
        '1. Atualizar o Orbit (nova versão do UA)<br>',
        '2. Usar a integração nativa com o Slack Desktop<br>',
        '3. Manter o Slack Desktop aberto e usar como janela overlay',
        '</div>',
        '<a href="https://app.slack.com/" style="background:#4a154b;color:#fff;padding:12px 28px;',
        'border-radius:8px;text-decoration:none;font-size:14px;font-weight:bold;">',
        'Tentar app.slack.com →</a>',
    ].join('');
    document.body.appendChild(d);
})();
"""


def is_slack_service(service_type: str) -> bool:
    """Return True for Slack service type."""
    return service_type.lower() == 'slack'


def get_slack_ua() -> str:
    """Return the current Slack Desktop user-agent string."""
    return SLACK_ELECTRON_UA


def get_slack_sec_ch_ua() -> str:
    """Return the Sec-CH-UA header value for Slack."""
    return SLACK_SEC_CH_UA

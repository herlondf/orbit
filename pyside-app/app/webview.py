"""
webview.py — Qt WebEngine wrapper for Orbit service tabs.

The key feature here is ServicePage.createWindow(), which intercepts ALL
new-window requests at the Chromium level (window.open, target="_blank",
OAuth redirects, iframes). This is the method that solves the Google login
problem that plagued the Tauri implementation.
"""
from __future__ import annotations

import os
import re

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from .storage import PROFILES_DIR
from .cookie_bridge import import_google_cookies
from .adblocker import is_blocked
from .slack_bridge import (
    is_slack_service, get_slack_ua, get_slack_sec_ch_ua,
    SLACK_STEALTH_JS, SLACK_BLOCKED_OVERLAY_JS,
)

_GOOGLE_TYPES = {'gmail', 'gchat', 'gmeet', 'gcal', 'google'}

# Module-level ad block state (shared across all profiles)
_ad_block_enabled = True

_interceptors: dict = {}  # keep interceptors alive (prevent GC)


def set_ad_block(enabled: bool):
    global _ad_block_enabled
    _ad_block_enabled = enabled

# Must match the Chromium version embedded in the installed PySide6
_CHROME_VER = '130'
USER_AGENT = (
    f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    f'AppleWebKit/537.36 (KHTML, like Gecko) '
    f'Chrome/{_CHROME_VER}.0.0.0 Safari/537.36'
)

# Injected at DocumentCreation in MainWorld.
# Covers every signal Google uses to detect embedded/automated browsers:
#   - navigator.webdriver (Chromium automation flag)
#   - navigator.userAgentData (User-Agent Client Hints JS API)
#   - window.chrome (extension runtime expected by Google pages)
#   - navigator.plugins (0 plugins signals headless)
#   - navigator.languages (empty array signals automation)
_STEALTH_JS = f"""
(function () {{
    // 1. Remove Chromium automation flag
    try {{
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
    }} catch(e) {{}}

    // 2. Spoof User-Agent Client Hints (navigator.userAgentData)
    //    Google reads this before checking the UA string.
    try {{
        const uaData = {{
            brands: [
                {{ brand: 'Chromium',     version: '{_CHROME_VER}' }},
                {{ brand: 'Google Chrome', version: '{_CHROME_VER}' }},
                {{ brand: 'Not?A_Brand',  version: '99'  }}
            ],
            mobile: false,
            platform: 'Windows',
            getHighEntropyValues: function(hints) {{
                return Promise.resolve({{
                    architecture: 'x86',
                    bitness: '64',
                    brands: this.brands,
                    fullVersionList: this.brands.map(b => ({{ brand: b.brand, version: b.version + '.0.0.0' }})),
                    mobile: false,
                    model: '',
                    platform: 'Windows',
                    platformVersion: '10.0.0',
                    uaFullVersion: '{_CHROME_VER}.0.0.0'
                }});
            }},
            toJSON: function() {{
                return {{ brands: this.brands, mobile: this.mobile, platform: this.platform }};
            }}
        }};
        Object.defineProperty(navigator, 'userAgentData', {{ get: () => uaData }});
    }} catch(e) {{}}

    // 3. Emulate Chrome extension runtime
    try {{
        if (!window.chrome) window.chrome = {{}};
        if (!window.chrome.runtime) window.chrome.runtime = {{}};
    }} catch(e) {{}}

    // 4. Non-empty plugins list (headless has 0)
    try {{
        Object.defineProperty(navigator, 'plugins', {{
            get: () => {{ const p = [1,2,3,4,5]; p.__proto__ = PluginArray.prototype; return p; }}
        }});
    }} catch(e) {{}}

    // 5. Realistic language list
    try {{
        Object.defineProperty(navigator, 'languages', {{ get: () => ['pt-BR','pt','en-US','en'] }});
    }} catch(e) {{}}
}})();
"""


# ── request interceptor ────────────────────────────────────────────────────────

class _StealthInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Adds HTTP-level Client Hints headers so Google's servers see the same
    signals as a real Chrome browser. JS spoofing covers the client side;
    this covers the network side.
    """
    _SEC_CH_UA = (
        f'"Chromium";v="{_CHROME_VER}", '
        f'"Google Chrome";v="{_CHROME_VER}", '
        f'"Not?A_Brand";v="99"'
    ).encode()

    def __init__(self, profile, user_agent: str = '', sec_ch_ua: str = ''):
        super().__init__(profile)
        self._ua = (user_agent or USER_AGENT).encode()
        self._sec_ch_ua = (sec_ch_ua or self._SEC_CH_UA.decode()).encode()

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        if _ad_block_enabled:
            url = info.requestUrl().toString()
            if is_blocked(url):
                info.block(True)
                return
        info.setHttpHeader(b'User-Agent', self._ua)
        info.setHttpHeader(b'Sec-CH-UA', self._sec_ch_ua)
        info.setHttpHeader(b'Sec-CH-UA-Mobile', b'?0')
        info.setHttpHeader(b'Sec-CH-UA-Platform', b'"Windows"')


# ── profile factory ────────────────────────────────────────────────────────────

def make_profile(profile_name: str, incognito: bool = False, proxy: str = '',
                  service_type: str = '', spellcheck: bool = True) -> QWebEngineProfile:
    """
    Create a Chromium profile for one service account.
    If incognito=True, an off-the-record (in-memory) profile is used.
    Each persistent account gets its own cookies, localStorage, IndexedDB, etc.
    For Slack, applies Electron-style UA + JS environment spoofing.
    """
    _is_slack = is_slack_service(service_type)
    effective_ua = get_slack_ua() if _is_slack else USER_AGENT
    effective_sec_ch_ua = get_slack_sec_ch_ua() if _is_slack else ''

    if incognito:
        profile = QWebEngineProfile()  # off-the-record / in-memory
        interceptor_key = f'incognito-{id(profile)}'
    else:
        profile = QWebEngineProfile(profile_name)
        storage_path = os.path.join(PROFILES_DIR, profile_name)
        os.makedirs(storage_path, exist_ok=True)
        profile.setPersistentStoragePath(storage_path)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        interceptor_key = profile_name

    profile.setHttpUserAgent(effective_ua)

    # HTTP-level stealth: add Client Hints headers to every request
    interceptor = _StealthInterceptor(profile, effective_ua, effective_sec_ch_ua)
    profile.setUrlRequestInterceptor(interceptor)
    _interceptors[interceptor_key] = interceptor  # prevent GC

    # JS-level stealth: base script + optional Slack-specific Electron spoof
    stealth = QWebEngineScript()
    stealth.setName('orbit-stealth')
    stealth.setSourceCode(SLACK_STEALTH_JS if _is_slack else _STEALTH_JS)
    stealth.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    stealth.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    stealth.setRunsOnSubFrames(True)
    profile.scripts().insert(stealth)

    # For Slack: inject fallback UI detector at DocumentReady
    if _is_slack:
        fallback = QWebEngineScript()
        fallback.setName('orbit-slack-fallback')
        fallback.setSourceCode(SLACK_BLOCKED_OVERLAY_JS)
        fallback.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        fallback.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        fallback.setRunsOnSubFrames(False)
        profile.scripts().insert(fallback)

    s = profile.settings()
    for attr, val in [
        (QWebEngineSettings.WebAttribute.JavascriptEnabled,               True),
        (QWebEngineSettings.WebAttribute.LocalStorageEnabled,              True),
        (QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,         True),
        (QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True),
        (QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,         True),
        (QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,      False),
        (QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled,            True),
    ]:
        s.setAttribute(attr, val)

    # Spellcheck support
    try:
        profile.setSpellCheckEnabled(spellcheck)
        profile.setSpellCheckLanguages(['en-US', 'pt-BR'])
    except Exception:
        pass  # Spellcheck may not be available in all builds

    return profile


# ── popup window ───────────────────────────────────────────────────────────────

class PopupView(QWebEngineView):  # pragma: no cover
    """
    Login / OAuth popup window.
    Uses the SAME QWebEngineProfile as the parent → shared cookies.
    After closing, the parent service page is reloaded to pick up the new
    session automatically.
    """

    def __init__(self, profile: QWebEngineProfile, on_close_reload=None):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowFlags(Qt.Window)
        self.resize(960, 720)
        self.setWindowTitle('Orbit – Login')

        page = _PopupPage(profile, self, on_close_reload=on_close_reload)
        self.setPage(page)


class _PopupPage(QWebEnginePage):  # pragma: no cover
    def __init__(self, profile, parent_view, on_close_reload=None):
        super().__init__(profile, parent_view)
        self._on_close_reload = on_close_reload
        self._parent_view = parent_view
        self.windowCloseRequested.connect(parent_view.close)
        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok: bool):
        """Detect Google's embedded-browser block and inject helpful overlay."""
        url = self.url().toString()
        if 'accounts.google.com' not in url:
            return

        check_js = """
(function() {
    var body = document.body ? document.body.innerText : '';
    return body.includes('may not be secure') ||
           body.includes('pode não ser seguro') ||
           body.includes('nicht sicher') ||
           body.includes('no es seguro') ||
           document.title.includes('Error');
})();
"""
        overlay_js = r"""
(function() {
    if (document.getElementById('orbit-overlay')) return;
    var d = document.createElement('div');
    d.id = 'orbit-overlay';
    d.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(30,30,46,0.97);'
        + 'z-index:99999;display:flex;flex-direction:column;align-items:center;'
        + 'justify-content:center;font-family:Segoe UI,sans-serif;color:#cdd6f4;padding:32px;';
    d.innerHTML = '<div style="font-size:56px;margin-bottom:16px;">🐙</div>'
        + '<div style="font-size:22px;font-weight:bold;margin-bottom:12px;">Login com Google</div>'
        + '<div style="font-size:14px;color:#a6adc8;text-align:center;max-width:420px;line-height:1.7;margin-bottom:24px;">'
        + 'O Google bloqueia login em navegadores embarcados por segurança.<br>'
        + 'Importe sua sessão do <b>Brave / Chrome / Edge</b>:</div>'
        + '<div style="background:#1e1e2e;border:1px solid #313244;border-radius:12px;padding:20px 28px;'
        + 'text-align:left;font-size:14px;line-height:2.2;margin-bottom:24px;">'
        + '<b>1.</b> Feche o Brave (ou Chrome/Edge)<br>'
        + '<b>2.</b> Clique com botão direito no serviço → <span style="color:#cba6f7">Sincronizar cookies</span><br>'
        + '<b>3.</b> Feche esta janela e recarregue<br>'
        + '</div>'
        + '<div style="background:#313244;color:#a6e3a1;padding:10px 20px;border-radius:8px;font-size:12px;">'
        + '💡 Você só precisa fazer isso uma vez — a sessão persiste</div>';
    document.body.appendChild(d);
})();
"""
        def maybe_inject(has_error):
            if has_error:
                self.runJavaScript(overlay_js)

        self.runJavaScript(check_js, 0, maybe_inject)

    def createWindow(self, win_type):
        # Allow nested popups (e.g., Google account chooser)
        nested = PopupView(self.profile(), on_close_reload=None)
        nested.resize(800, 600)
        nested.show()
        return nested.page()

    def javaScriptConsoleMessage(self, level, msg, line, source):
        pass  # suppress service-page console noise


# ── service page ───────────────────────────────────────────────────────────────

class ServicePage(QWebEnginePage):  # pragma: no cover
    """
    Custom QWebEnginePage for embedded service tabs.

    createWindow() is the critical method — called by Chromium for EVERY
    new-window request regardless of origin (main frame, iframes, cross-origin).
    This is what makes Google login work.
    """

    def __init__(self, profile: QWebEngineProfile, parent_view: 'ServiceView'):
        super().__init__(profile, parent_view)
        self._parent_view = parent_view

    def createWindow(self, win_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        """
        Called by Chromium whenever a page wants to open a new window:
          - window.open(url)
          - <a target="_blank">
          - Google Sign-In button (opens accounts.google.com)
          - OAuth flows, Microsoft login, etc.

        We open a popup using the SAME profile so cookies are shared.
        When the popup closes, we reload the service page so it picks up the
        logged-in session.
        """
        def on_popup_close():
            if not self._parent_view.is_destroyed:
                self._parent_view.reload()

        popup = PopupView(self.profile(), on_close_reload=on_popup_close)
        popup.destroyed.connect(on_popup_close)
        popup.show()
        # Qt will load the target URL into popup.page() automatically
        return popup.page()

    def javaScriptConsoleMessage(self, level, msg, line, source):
        pass


# ── service view ───────────────────────────────────────────────────────────────

class ServiceView(QWebEngineView):  # pragma: no cover
    """
    Embedded browser for a single service account.
    - Isolated session via QWebEngineProfile
    - Badge counting via page title "(N) Service Name" pattern
    - New-window interception via ServicePage.createWindow()
    - Google services: Chrome cookies imported automatically to bypass login block
    """

    badge_changed = Signal(int)
    load_status_changed = Signal(str)

    def __init__(self, profile_name: str, url: str, service_type: str = '', custom_css: str = '', custom_js: str = '', zoom: float = 1.0, incognito: bool = False, spellcheck: bool = True, parent=None):
        super().__init__(parent)
        self.is_destroyed = False
        self._url = url
        self._status: str = 'idle'

        self._profile = make_profile(profile_name, incognito=incognito, service_type=service_type, spellcheck=spellcheck)

        # Google blocks OAuth in embedded WebViews at the binary level.
        # Importing existing Chrome cookies lets the user skip the login entirely.
        # Skip cookie import for incognito profiles (no persistence).
        if not incognito and any(t in service_type for t in _GOOGLE_TYPES):
            imported = import_google_cookies(self._profile)
            if imported:
                print(f'[cookie_bridge] imported {imported} Google cookies from Chrome')

        if custom_css:
            css_script = QWebEngineScript()
            css_script.setName('orbit-custom-css')
            css_script.setSourceCode(
                f'(function(){{ var s=document.createElement("style"); '
                f's.textContent={repr(custom_css)}; document.head.appendChild(s); }})();'
            )
            css_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            css_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            css_script.setRunsOnSubFrames(True)
            self._profile.scripts().insert(css_script)

        if custom_js:
            js_script = QWebEngineScript()
            js_script.setName('orbit-custom-js')
            js_script.setSourceCode(custom_js)
            js_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            js_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            js_script.setRunsOnSubFrames(False)
            self._profile.scripts().insert(js_script)

        self._page = ServicePage(self._profile, self)
        self.setPage(self._page)

        self._page.titleChanged.connect(self._on_title_changed)
        self._page.loadStarted.connect(lambda: self._on_load_status('loading'))
        self._page.loadFinished.connect(lambda ok: self._on_load_status('ready' if ok else 'error'))

        self.load(QUrl(url))
        self.setZoomFactor(zoom)

    @property
    def status(self) -> str:
        return self._status

    def _on_load_status(self, status: str):
        self._status = status
        self.load_status_changed.emit(status)

    def _on_title_changed(self, title: str):
        m = re.match(r'\((\d+)\)', title)
        self.badge_changed.emit(int(m.group(1)) if m else 0)

    def set_zoom(self, factor: float):
        self.setZoomFactor(factor)

    def closeEvent(self, event):
        self.is_destroyed = True
        super().closeEvent(event)

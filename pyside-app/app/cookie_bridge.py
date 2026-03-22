"""
cookie_bridge.py — Import browser cookies into QWebEngineProfile.

Google blocks OAuth login inside embedded WebViews. The workaround is to
import the user's existing Google session from Chrome/Brave/Edge/Firefox/Opera.

Chromium-based browsers (Brave, Chrome, Edge, Opera, Vivaldi):
  - v10 cookies: decrypted via AES-256-GCM with DPAPI master key (old browsers)
  - v20 cookies: decrypted via CDP (Chrome DevTools Protocol) — launched headless
    with the user's own profile so Brave/Chrome can decrypt internally.

Firefox/Waterfox:
  - Cookies stored as plain text in SQLite (moz_cookies table).
  - No decryption needed; file can be copied while Firefox is closed.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import List, Optional, Tuple

from PySide6.QtCore import QDateTime, QUrl
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtWebEngineCore import QWebEngineProfile

_IS_WINDOWS = sys.platform == 'win32'

# ── browser registry ──────────────────────────────────────────────────────────
# Chromium-based: (name, user_data_rel, base_env, process_exe)
# base_env: 'LOCALAPPDATA' or 'APPDATA'
_CHROMIUM_BROWSERS: List[Tuple[str, str, str, str]] = [
    ('Brave',    r'BraveSoftware\Brave-Browser\User Data', 'LOCALAPPDATA', 'brave.exe'),
    ('Chrome',   r'Google\Chrome\User Data',               'LOCALAPPDATA', 'chrome.exe'),
    ('Edge',     r'Microsoft\Edge\User Data',              'LOCALAPPDATA', 'msedge.exe'),
    ('Opera',    r'Opera Software\Opera Stable',           'APPDATA',      'opera.exe'),
    ('Opera GX', r'Opera Software\Opera GX Stable',        'APPDATA',      'opera.exe'),
    ('Chromium', r'Chromium\User Data',                    'LOCALAPPDATA', 'chromium.exe'),
    ('Vivaldi',  r'Vivaldi\User Data',                     'LOCALAPPDATA', 'vivaldi.exe'),
]

# Firefox-based: (name, profiles_rel, base_env, process_exe)
_FIREFOX_BROWSERS: List[Tuple[str, str, str, str]] = [
    ('Firefox',   r'Mozilla\Firefox\Profiles',  'APPDATA', 'firefox.exe'),
    ('Waterfox',  r'Waterfox\Profiles',          'APPDATA', 'waterfox.exe'),
    ('LibreWolf', r'LibreWolf\Profiles',         'APPDATA', 'librewolf.exe'),
]

# Candidates for browser executable paths (searched in order)
_CHROMIUM_EXE_CANDIDATES = {
    'Brave':    [r'LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe',
                 r'PROGRAMFILES\BraveSoftware\Brave-Browser\Application\brave.exe',
                 r'PROGRAMFILES(X86)\BraveSoftware\Brave-Browser\Application\brave.exe'],
    'Chrome':   [r'LOCALAPPDATA\Google\Chrome\Application\chrome.exe',
                 r'PROGRAMFILES\Google\Chrome\Application\chrome.exe',
                 r'PROGRAMFILES(X86)\Google\Chrome\Application\chrome.exe'],
    'Edge':     [r'PROGRAMFILES\Microsoft\Edge\Application\msedge.exe',
                 r'PROGRAMFILES(X86)\Microsoft\Edge\Application\msedge.exe',
                 r'LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe'],
    'Opera':    [r'LOCALAPPDATA\Programs\Opera\opera.exe',
                 r'PROGRAMFILES\Opera\opera.exe'],
    'Opera GX': [r'LOCALAPPDATA\Programs\Opera GX\opera.exe',
                 r'PROGRAMFILES\Opera GX\opera.exe'],
    'Chromium': [r'LOCALAPPDATA\Chromium\Application\chrome.exe'],
    'Vivaldi':  [r'LOCALAPPDATA\Vivaldi\Application\vivaldi.exe',
                 r'PROGRAMFILES\Vivaldi\Application\vivaldi.exe'],
}

# Keep legacy alias for external callers
_BROWSERS = [(n, r, e) for n, r, _, e in _CHROMIUM_BROWSERS]


# ── browser detection ──────────────────────────────────────────────────────────

def _resolve_path(template: str) -> str:
    """Expand env-variable prefix in a path template like 'LOCALAPPDATA\\foo'."""
    parts = template.split('\\', 1)
    base = os.environ.get(parts[0], '')
    return os.path.join(base, parts[1]) if len(parts) > 1 else base


def find_browser() -> Optional[Tuple[str, str, str]]:
    """Return (name, user_data_dir, exe) for the first installed Chromium browser."""
    for name, rel, base_env, exe in _CHROMIUM_BROWSERS:
        base = os.environ.get(base_env, '')
        path = os.path.join(base, rel)
        if os.path.isdir(path):
            return name, path, exe
    return None


def find_all_browsers() -> List[dict]:
    """Return info dicts for all detected browsers (Chromium + Firefox)."""
    browsers = []
    for name, rel, base_env, exe in _CHROMIUM_BROWSERS:
        base = os.environ.get(base_env, '')
        path = os.path.join(base, rel)
        if os.path.isdir(path):
            browsers.append({'name': name, 'type': 'chromium',
                             'user_data_dir': path, 'exe': exe})
    for name, rel, base_env, exe in _FIREFOX_BROWSERS:
        base = os.environ.get(base_env, '')
        path = os.path.join(base, rel)
        if os.path.isdir(path):
            browsers.append({'name': name, 'type': 'firefox',
                             'profiles_dir': path, 'exe': exe})
    return browsers


def find_chromium_exe(name: str) -> Optional[str]:
    """Find the full path to the browser executable."""
    for template in _CHROMIUM_EXE_CANDIDATES.get(name, []):
        path = _resolve_path(template)
        if os.path.exists(path):
            return path
    return None


def is_browser_running(exe: Optional[str] = None) -> bool:
    """Return True if the specified browser exe (or any Chromium browser) is running.

    When *exe* is given, only that process is checked (e.g. 'brave.exe').
    """
    if not _IS_WINDOWS:
        return False
    targets = [exe] if exe else [e for _, _, _, e in _CHROMIUM_BROWSERS]
    for target in targets:
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {target}', '/NH'],
                capture_output=True, text=True, timeout=5,
            )
            if target.lower() in result.stdout.lower():
                return True
        except Exception:
            pass
    return False


# ── Chromium v10 decryption (AES-256-GCM + DPAPI) ────────────────────────────

def _get_aes_key(user_data_dir: str) -> Optional[bytes]:
    """Read and DPAPI-decrypt the browser's AES-256-GCM master key (Windows only)."""
    if not _IS_WINDOWS:
        return None
    local_state_path = os.path.join(user_data_dir, 'Local State')
    if not os.path.exists(local_state_path):
        return None
    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        enc_key = base64.b64decode(state['os_crypt']['encrypted_key'])[5:]  # strip 'DPAPI'
        import win32crypt  # noqa: PLC0415
        return win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]
    except Exception:
        return None


def _decrypt_value(enc: bytes, key: bytes) -> Optional[str]:
    """Decrypt a single Chromium cookie value (AES-256-GCM v10 or legacy DPAPI)."""
    try:
        if enc[:3] == b'v10':
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415
            return AESGCM(key).decrypt(enc[3:15], enc[15:], None).decode('utf-8')
        # v20 uses App-Bound Encryption — cannot be decrypted here; use CDP instead
        if enc[:3] == b'v20':
            return None
        if _IS_WINDOWS and enc:
            import win32crypt  # noqa: PLC0415
            return win32crypt.CryptUnprotectData(enc, None, None, None, 0)[1].decode('utf-8')
    except Exception:
        pass
    return None


def _read_chromium_cookies_sqlite(user_data_dir: str) -> Tuple[List[dict], bool]:
    """
    Try to read Google cookies from Chromium's SQLite DB using v10 decryption.
    Returns (cookies, has_v20) where has_v20=True means v20 cookies were found
    and CDP decryption should be attempted.
    """
    key = _get_aes_key(user_data_dir)
    if key is None:
        return [], False

    default_dir = os.path.join(user_data_dir, 'Default')
    cookies_db = None
    for rel in (r'Network\Cookies', 'Cookies'):
        candidate = os.path.join(default_dir, rel)
        if os.path.exists(candidate):
            cookies_db = candidate
            break
    if not cookies_db:
        return [], False

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
    os.close(tmp_fd)
    try:
        shutil.copy2(cookies_db, tmp_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return [], False

    result, has_v20 = [], False
    try:
        conn = sqlite3.connect(f'file:{tmp_path}?mode=ro', uri=True)
        rows = conn.execute(
            """
            SELECT host_key, name, encrypted_value, path,
                   expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE host_key LIKE '%google.com' OR host_key LIKE '%gmail.com'
            """
        ).fetchall()
        conn.close()
    except Exception:
        rows = []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    for host, name, enc_val, path, expires_utc, is_secure, is_httponly in rows:
        if enc_val[:3] == b'v20':
            has_v20 = True
            continue
        value = _decrypt_value(enc_val, key)
        if value is None:
            continue
        result.append({
            'domain': host, 'name': name, 'value': value,
            'path': path or '/', 'expires_utc': expires_utc,
            'secure': bool(is_secure), 'http_only': bool(is_httponly),
        })
    return result, has_v20


# ── Chromium v20 decryption via CDP ──────────────────────────────────────────

def _extract_cookies_via_cdp(exe_path: str, user_data_dir: str) -> List[dict]:
    """
    Launch browser headless with remote debugging, extract all Google cookies
    via Chrome DevTools Protocol (CDP). Works for v20 cookies because the
    browser binary decrypts them internally.
    """
    with socket.socket() as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    flags = subprocess.CREATE_NO_WINDOW if _IS_WINDOWS else 0
    proc = subprocess.Popen(
        [exe_path,
         f'--remote-debugging-port={port}',
         f'--user-data-dir={user_data_dir}',
         '--remote-allow-origins=*',
         '--headless=new',
         '--no-first-run',
         '--no-default-browser-check',
         '--disable-extensions',
         '--disable-sync',
         '--disable-gpu',
         '--disable-background-networking'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags,
    )

    ws_url = None
    try:
        for _ in range(40):   # wait up to 20 s
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/json/version', timeout=2
                ) as r:
                    info = json.loads(r.read())
                    ws_url = info.get('webSocketDebuggerUrl', '').replace(
                        'localhost', '127.0.0.1')
                    if ws_url:
                        break
            except Exception:
                pass

        if not ws_url:
            return []

        import websocket  # noqa: PLC0415
        ws = websocket.create_connection(ws_url, timeout=15)

        def _send_and_wait(cmd_id: int, method: str, params: dict = None):
            payload = {'id': cmd_id, 'method': method}
            if params:
                payload['params'] = params
            ws.send(json.dumps(payload))
            for _ in range(50):
                msg = json.loads(ws.recv())
                if msg.get('id') == cmd_id:
                    return msg.get('result', {})
            return {}

        raw_cookies = []
        try:
            # Try Storage.getCookies on browser target (works in Chrome 100+)
            result_data = _send_and_wait(1, 'Storage.getCookies')
            raw_cookies = result_data.get('cookies', [])

            # Fallback: create a tab and use Network.getAllCookies
            if not raw_cookies:
                _send_and_wait(2, 'Target.createTarget', {'url': 'about:blank'})
                time.sleep(1)
                # Get the new target's WS URL
                with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/json/list', timeout=5
                ) as r:
                    targets = json.loads(r.read())
                if targets:
                    tab_ws = targets[0]['webSocketDebuggerUrl'].replace('localhost', '127.0.0.1')
                    tab = websocket.create_connection(tab_ws, timeout=10)
                    try:
                        tab.send(json.dumps({'id': 1, 'method': 'Network.enable'}))
                        tab.recv()
                        tab.send(json.dumps({'id': 2, 'method': 'Network.getAllCookies'}))
                        for _ in range(30):
                            msg = json.loads(tab.recv())
                            if msg.get('id') == 2:
                                raw_cookies = msg.get('result', {}).get('cookies', [])
                                break
                    finally:
                        tab.close()
        finally:
            ws.close()

        def _unix_to_chrome(ts: float) -> int:
            return int((ts + 11_644_473_600) * 1_000_000) if ts > 0 else 0

        result = []
        for c in raw_cookies:
            domain = c.get('domain', '')
            if 'google.com' not in domain and 'gmail.com' not in domain:
                continue
            result.append({
                'domain': domain,
                'name': c.get('name', ''),
                'value': c.get('value', ''),
                'path': c.get('path', '/'),
                'expires_utc': _unix_to_chrome(c.get('expires', -1)),
                'secure': c.get('secure', False),
                'http_only': c.get('httpOnly', False),
            })
        return result

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


# ── Firefox cookie reading ────────────────────────────────────────────────────

def _read_firefox_google_cookies(profiles_dir: str) -> List[dict]:
    """
    Read Google cookies from Firefox's plain-text SQLite (moz_cookies).
    No encryption needed for standard Firefox profiles.
    """
    if not os.path.isdir(profiles_dir):
        return []

    profiles = sorted(
        [os.path.join(profiles_dir, d) for d in os.listdir(profiles_dir)
         if os.path.isdir(os.path.join(profiles_dir, d))],
        key=lambda p: os.path.getmtime(p), reverse=True,
    )

    result = []
    for profile in profiles:
        cookies_db = os.path.join(profile, 'cookies.sqlite')
        if not os.path.exists(cookies_db):
            continue
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
        os.close(tmp_fd)
        try:
            shutil.copy2(cookies_db, tmp_path)
            conn = sqlite3.connect(f'file:{tmp_path}?mode=ro', uri=True)
            rows = conn.execute(
                """SELECT host, name, value, path, expiry, isSecure, isHttpOnly
                   FROM moz_cookies
                   WHERE host LIKE '%google.com' OR host LIKE '%gmail.com'"""
            ).fetchall()
            conn.close()
            for host, name, value, path, expiry, is_secure, is_httponly in rows:
                chrome_epoch = int((expiry + 11_644_473_600) * 1_000_000) if expiry > 0 else 0
                result.append({
                    'domain': host, 'name': name, 'value': value or '',
                    'path': path or '/', 'expires_utc': chrome_epoch,
                    'secure': bool(is_secure), 'http_only': bool(is_httponly),
                })
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    return result


# ── main public API ───────────────────────────────────────────────────────────

def read_chrome_google_cookies() -> List[dict]:
    """
    Read and decrypt Google-domain cookies from any installed browser.
    Tries Chromium browsers first (v10 SQLite → v20 CDP → next browser),
    then Firefox. Returns empty list on total failure.
    The browser MUST be closed before calling this.
    """
    # Try Chromium browsers
    for name, rel, base_env, exe in _CHROMIUM_BROWSERS:
        base = os.environ.get(base_env, '')
        user_data_dir = os.path.join(base, rel)
        if not os.path.isdir(user_data_dir):
            continue

        cookies, has_v20 = _read_chromium_cookies_sqlite(user_data_dir)

        if cookies:
            return cookies  # v10 succeeded

        if has_v20:
            # v20 cookies — try CDP
            exe_path = find_chromium_exe(name)
            if exe_path:
                try:
                    cdp_cookies = _extract_cookies_via_cdp(exe_path, user_data_dir)
                    if cdp_cookies:
                        return cdp_cookies
                except Exception:
                    pass

    # Try Firefox-based browsers
    for name, rel, base_env, exe in _FIREFOX_BROWSERS:
        base = os.environ.get(base_env, '')
        profiles_dir = os.path.join(base, rel)
        cookies = _read_firefox_google_cookies(profiles_dir)
        if cookies:
            return cookies

    return []


# ── Qt integration ─────────────────────────────────────────────────────────────

def _chrome_epoch_to_qt(chrome_utc: int) -> QDateTime:
    """Chrome epoch = microseconds since 1601-01-01. Convert to QDateTime."""
    unix_secs = (chrome_utc // 1_000_000) - 11_644_473_600
    return QDateTime.fromSecsSinceEpoch(max(0, int(unix_secs)))


def import_google_cookies(profile: QWebEngineProfile) -> int:
    """
    Import Google cookies from any browser into *profile*.
    Returns the number of cookies imported. Must be called from the main Qt thread.
    """
    raw = read_chrome_google_cookies()
    if not raw:
        return 0

    store = profile.cookieStore()
    count = 0
    for c in raw:
        try:
            cookie = QNetworkCookie()
            cookie.setDomain(c['domain'])
            cookie.setName(c['name'].encode('utf-8'))
            cookie.setValue(c['value'].encode('utf-8'))
            cookie.setPath(c['path'])
            cookie.setSecure(c['secure'])
            cookie.setHttpOnly(c['http_only'])
            if c['expires_utc'] and c['expires_utc'] > 0:
                cookie.setExpirationDate(_chrome_epoch_to_qt(c['expires_utc']))
            domain = c['domain'].lstrip('.')
            store.setCookie(cookie, QUrl(f'https://{domain}'))
            count += 1
        except Exception:
            continue
    return count


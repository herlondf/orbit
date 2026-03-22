"""webdav_sync.py — WebDAV/cloud sync for Orbit backups."""
from __future__ import annotations
import datetime
from typing import Optional


class WebDAVSync:
    """Client for syncing Orbit backups to a WebDAV server."""

    def __init__(self):
        self._url: str = ''
        self._username: str = ''
        self._password: str = ''

    def configure(self, url: str, username: str = '', password: str = '') -> None:
        """Configure the WebDAV connection."""
        self._url = url.rstrip('/')
        self._username = username
        self._password = password

    @staticmethod
    def backup_filename() -> str:
        """Generate a timestamped backup filename."""
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        return f'orbit-backup-{ts}.json'

    def _auth(self):
        if self._username:
            return (self._username, self._password)
        return None

    def test_connection(self) -> tuple[bool, str]:
        """Test the WebDAV connection. Returns (ok, message)."""
        try:
            import requests
            resp = requests.request(
                'PROPFIND', self._url,
                auth=self._auth(),
                headers={'Depth': '0'},
                timeout=10,
            )
            if resp.status_code in (207, 200, 401):
                if resp.status_code == 401:
                    return False, 'Autenticação falhou (401)'
                return True, f'Conexão OK (HTTP {resp.status_code})'
            return False, f'Resposta inesperada: HTTP {resp.status_code}'
        except ImportError:
            return False, 'Biblioteca requests não encontrada'
        except Exception as e:
            return False, f'Erro de conexão: {e}'

    def upload_data(self, filename: str, data: bytes) -> bool:
        """Upload data bytes to the WebDAV server."""
        try:
            import requests
            url = f'{self._url}/{filename}'
            resp = requests.put(
                url,
                data=data,
                auth=self._auth(),
                headers={'Content-Type': 'application/json'},
                timeout=30,
            )
            return resp.status_code in (200, 201, 204)
        except Exception:
            return False

    def download_data(self, filename: str) -> Optional[bytes]:
        """Download a file from the WebDAV server."""
        try:
            import requests
            url = f'{self._url}/{filename}'
            resp = requests.get(url, auth=self._auth(), timeout=30)
            if resp.status_code == 200:
                return resp.content
            return None
        except Exception:
            return None

    def list_backups(self) -> list[str]:
        """List backup files on the WebDAV server."""
        try:
            import requests
            resp = requests.request(
                'PROPFIND', self._url,
                auth=self._auth(),
                headers={'Depth': '1'},
                timeout=10,
            )
            if resp.status_code != 207:
                return []
            # Parse basic filenames from XML response
            import re
            names = re.findall(r'<d:href>([^<]+orbit-backup[^<]+\.json)</d:href>', resp.text)
            return [n.split('/')[-1] for n in names]
        except Exception:
            return []


_webdav_instance: Optional[WebDAVSync] = None


def get_webdav() -> WebDAVSync:
    """Get or create the global WebDAVSync instance."""
    global _webdav_instance
    if _webdav_instance is None:
        _webdav_instance = WebDAVSync()
    return _webdav_instance


def save_webdav_config(url: str, username: str, password: str) -> None:
    """Save WebDAV config to settings."""
    from .storage import load_settings, save_settings
    settings = load_settings()
    settings['webdav'] = {
        'url': url,
        'username': username,
        'password': password,
    }
    save_settings(settings)


def load_webdav_config() -> dict:
    """Load WebDAV config from settings."""
    from .storage import load_settings
    settings = load_settings()
    return settings.get('webdav', {})


def init_from_settings() -> bool:
    """Initialize WebDAV from saved settings. Returns True if configured."""
    cfg = load_webdav_config()
    if not cfg.get('url'):
        return False
    wd = get_webdav()
    wd.configure(cfg['url'], cfg.get('username', ''), cfg.get('password', ''))
    return True

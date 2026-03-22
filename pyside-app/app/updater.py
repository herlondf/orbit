"""
updater.py — Auto-update system for Orbit.

Checks https://github.com/herlondf/orbit/releases for new versions.
Downloads and installs the MSI/ZIP update with progress reporting.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from typing import Callable, Optional

APP_VERSION = '1.0.0'
GITHUB_REPO = 'herlondf/orbit'
RELEASES_URL = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
MANIFEST_URL = f'https://github.com/{GITHUB_REPO}/releases/latest/download/latest.json'

_HEADERS = {
    'User-Agent': f'Orbit-Updater/{APP_VERSION}',
    'Accept': 'application/vnd.github+json',
}


def check_for_update() -> tuple[bool, str, str, str]:
    """
    Check GitHub Releases for a newer version.
    Returns (has_update, latest_version, release_url, download_url).
    Safe to call from any thread.
    """
    try:
        req = urllib.request.Request(RELEASES_URL, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        latest = data.get('tag_name', '').lstrip('v')
        html_url = data.get('html_url', '')

        # Find MSI asset (preferred) then ZIP fallback
        download_url = ''
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if name.endswith('.msi') and 'win-x64' in name:
                download_url = asset.get('browser_download_url', '')
                break
        if not download_url:
            for asset in data.get('assets', []):
                name = asset.get('name', '')
                if name.endswith('.zip') and 'win-x64' in name:
                    download_url = asset.get('browser_download_url', '')
                    break

        if latest and _version_gt(latest, APP_VERSION):
            return True, latest, html_url, download_url
        return False, latest, html_url, download_url

    except Exception:
        return False, '', '', ''


def get_changelog(version: str) -> str:
    """Fetch release notes for a specific version from GitHub API."""
    try:
        url = f'https://api.github.com/repos/{GITHUB_REPO}/releases/tags/v{version}'
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get('body', '')
    except Exception:
        return ''


def download_update(
    url: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Download update file to a temp file.
    progress_cb(downloaded_bytes, total_bytes) called during download.
    Returns path to downloaded file.
    """
    ext = '.msi' if url.endswith('.msi') else '.zip'
    fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix='orbit-update-')
    os.close(fd)

    req = urllib.request.Request(url, headers={'User-Agent': f'Orbit-Updater/{APP_VERSION}'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        chunk = 65536
        with open(tmp_path, 'wb') as f:
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
                downloaded += len(data)
                if progress_cb:
                    progress_cb(downloaded, total)

    return tmp_path


def install_update(file_path: str) -> None:
    """
    Launch the installer and quit the app.
    For MSI: msiexec /i — silent install
    For ZIP: open folder and instruct user
    """
    if file_path.endswith('.msi'):
        subprocess.Popen(
            ['msiexec', '/i', file_path, '/qb'],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
    else:
        # ZIP: open containing folder
        os.startfile(os.path.dirname(file_path))

    # Quit the current app
    from PySide6.QtWidgets import QApplication
    QApplication.quit()


def _version_gt(a: str, b: str) -> bool:
    def parse(v):
        try:
            return tuple(int(x) for x in v.split('.'))
        except Exception:
            return (0,)
    return parse(a) > parse(b)

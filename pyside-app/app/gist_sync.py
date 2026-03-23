from __future__ import annotations

import json
import urllib.request
import urllib.error

GIST_API = 'https://api.github.com/gists'


def _headers(token: str) -> dict:
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'Orbit/1.0',
    }


def create_gist(token: str, content: str) -> str:
    """Create a new private gist. Returns gist ID."""
    payload = json.dumps({
        'description': 'Orbit Backup',
        'public': False,
        'files': {'Orbit_backup.json': {'content': content}},
    }).encode()
    req = urllib.request.Request(GIST_API, data=payload, headers=_headers(token), method='POST')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['id']


def update_gist(token: str, gist_id: str, content: str) -> None:
    """Update existing gist."""
    payload = json.dumps({
        'files': {'Orbit_backup.json': {'content': content}},
    }).encode()
    req = urllib.request.Request(
        f'{GIST_API}/{gist_id}', data=payload, headers=_headers(token), method='PATCH'
    )
    with urllib.request.urlopen(req):
        pass


def fetch_gist(token: str, gist_id: str) -> str:
    """Fetch gist content."""
    req = urllib.request.Request(f'{GIST_API}/{gist_id}', headers=_headers(token))
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        return data['files']['Orbit_backup.json']['content']


def list_user_gists(token: str) -> list:
    """List gists to find existing Orbit backup."""
    req = urllib.request.Request(GIST_API, headers=_headers(token))
    with urllib.request.urlopen(req) as r:
        gists = json.loads(r.read())
        return [g for g in gists if 'Orbit_backup.json' in g.get('files', {})]

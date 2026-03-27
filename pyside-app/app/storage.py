from __future__ import annotations

import json
import os
from typing import List

from .models import Account, Service, ServiceGroup, Workspace
from .encryption import dpapi_protect, dpapi_unprotect

_APPDATA = os.environ.get('APPDATA', os.path.expanduser('~'))
STORAGE_DIR = os.path.join(_APPDATA, 'Orbit')
STORAGE_FILE = os.path.join(STORAGE_DIR, 'workspace.json')
PROFILES_DIR = os.path.join(STORAGE_DIR, 'profiles')
_WORKSPACES_FILE = os.path.join(STORAGE_DIR, 'workspaces.json')


def _ensure_dirs() -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)


import base64
import logging
from urllib.parse import urlparse, urlunparse

_log = logging.getLogger(__name__)


def _protect_proxy(proxy: str) -> str:
    """Encrypt the password portion of a proxy URL with DPAPI before saving."""
    if not proxy:
        return proxy
    try:
        p = urlparse(proxy)
        if p.password:
            enc = base64.b64encode(dpapi_protect(p.password.encode('utf-8'))).decode('ascii')
            netloc = f"{p.username}:{{dpapi}}{enc}@{p.hostname}"
            if p.port:
                netloc += f":{p.port}"
            return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))
    except Exception:
        _log.debug("DPAPI protect failed for proxy, storing as-is")
    return proxy


def _unprotect_proxy(proxy: str) -> str:
    """Decrypt the DPAPI-protected password portion of a proxy URL on load."""
    if not proxy or '{dpapi}' not in proxy:
        return proxy
    try:
        p = urlparse(proxy)
        if p.password and p.password.startswith('{dpapi}'):
            enc = p.password[7:]  # strip {dpapi} prefix
            password = dpapi_unprotect(base64.b64decode(enc)).decode('utf-8')
            netloc = f"{p.username}:{password}@{p.hostname}"
            if p.port:
                netloc += f":{p.port}"
            return urlunparse((p.scheme, netloc, p.path, p.params, p.query, p.fragment))
    except Exception:
        _log.debug("DPAPI unprotect failed for proxy, returning as-is")
    return proxy


def _service_to_dict(svc: Service) -> dict:
    return {
        'id': svc.id,
        'service_type': svc.service_type,
        'name': svc.name,
        'icon': svc.icon,
        'color': svc.color,
        'unread': svc.unread,
        'hibernate_after': svc.hibernate_after,
        'pinned': svc.pinned,
        'custom_css': svc.custom_css,
        'custom_js': svc.custom_js,
        'zoom': svc.zoom,
        'notification_sound': svc.notification_sound,
        'incognito': svc.incognito,
        'proxy': _protect_proxy(svc.proxy),
        'enabled': svc.enabled,
        'tags': svc.tags,
        'spellcheck': svc.spellcheck,
        'preload': svc.preload,
        'accounts': [
            {
                'id': a.id,
                'label': a.label,
                'url': a.url,
                'profile_name': a.profile_name,
                'notifications': a.notifications,
                'authuser': a.authuser,
            }
            for a in svc.accounts
        ],
    }


def _service_from_dict(s: dict) -> Service:
    accounts = [
        Account(
            id=a['id'],
            label=a['label'],
            url=a['url'],
            profile_name=a['profile_name'],
            notifications=a.get('notifications', 'native'),
            authuser=a.get('authuser', 0),
        )
        for a in s.get('accounts', [])
    ]
    return Service(
        id=s['id'],
        service_type=s.get('service_type', s['id']),
        name=s['name'],
        icon=s['icon'],
        color=s['color'],
        accounts=accounts,
        unread=s.get('unread', 0),
        hibernate_after=s.get('hibernate_after'),
        pinned=s.get('pinned', False),
        custom_css=s.get('custom_css', ''),
        custom_js=s.get('custom_js', ''),
        zoom=s.get('zoom', 1.0),
        notification_sound=s.get('notification_sound', ''),
        incognito=s.get('incognito', False),
        proxy=_unprotect_proxy(s.get('proxy', '')),
        enabled=s.get('enabled', True),
        tags=s.get('tags', []),
        spellcheck=s.get('spellcheck', True),
        preload=s.get('preload', False),
    )


def _group_to_dict(g: ServiceGroup) -> dict:
    return {
        'id': g.id,
        'name': g.name,
        'service_ids': list(g.service_ids),
        'collapsed': g.collapsed,
    }


def _group_from_dict(d: dict) -> ServiceGroup:
    return ServiceGroup(
        id=d['id'],
        name=d['name'],
        service_ids=list(d.get('service_ids', [])),
        collapsed=d.get('collapsed', False),
    )


def save_services(services: List[Service]) -> None:
    _ensure_dirs()
    data = [_service_to_dict(svc) for svc in services]
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_services() -> List[Service]:
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return [_service_from_dict(s) for s in data]
    except Exception:
        return []


_SETTINGS_FILE = os.path.join(STORAGE_DIR, 'settings.json')

# Default values for all known settings keys.
SETTINGS_DEFAULTS: dict = {
    'theme': 'dark',
    'accent': 'Iris',
    'sidebar_compact': True,           # sidebar starts minimized by default
    'sidebar_compact_width': 68,       # px — width when minimized
    'sidebar_expanded_width': 220,     # px — width when expanded
    'sidebar_width': 68,               # last saved splitter position
    'ad_block': True,
    'minimize_to_tray': False,         # close button hides to tray
    'show_tray': True,                 # show system tray icon
    'ai_sidebar_open': False,
    'encrypt_enabled': False,
    'workspaces_enabled': True,        # show workspace switcher in sidebar
    'preload_on_start': False,         # pre-warm all services on startup
    'notification_style': 'orbit',    # 'orbit' | 'system' | 'both'
    'sidebar_style': 'discord',       # 'discord' | 'arc' | 'dock' | 'notion'
}


def load_settings() -> dict:
    if not os.path.exists(_SETTINGS_FILE):
        return {}
    try:
        with open(_SETTINGS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: dict) -> None:
    _ensure_dirs()
    with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_DEFAULT_SHORTCUTS = {
    'focus_mode':   'Ctrl+B',
    'palette':      'Ctrl+K',
    'zoom_in':      'Ctrl+=',
    'zoom_out':     'Ctrl+-',
    'zoom_reset':   'Ctrl+0',
    'dnd_toggle':   'Ctrl+D',
    'quick_switch': 'Alt+`',
}


def load_shortcuts() -> dict:
    settings = load_settings()
    saved = settings.get('shortcuts', {})
    return {**_DEFAULT_SHORTCUTS, **saved}


def save_shortcuts(shortcuts: dict) -> None:
    settings = load_settings()
    settings['shortcuts'] = shortcuts
    save_settings(settings)


def load_workspaces() -> List[Workspace]:
    from .encryption import read_json_file, get_session_password
    if os.path.exists(_WORKSPACES_FILE):
        try:
            data = read_json_file(_WORKSPACES_FILE, password=get_session_password())
            if isinstance(data, list):
                result = []
                for w in data:
                    services = [_service_from_dict(s) for s in w.get('services', [])]
                    groups = [_group_from_dict(g) for g in w.get('groups', [])]
                    result.append(Workspace(id=w['id'], name=w['name'], services=services, groups=groups, accent=w.get('accent', ''), bg_color=w.get('bg_color', '')))
                if result:
                    return result
        except Exception:
            pass
    # Migrate from old workspace.json
    services = load_services()
    ws = Workspace(id='ws-default', name='Principal', services=services)
    return [ws]


def save_workspaces(workspaces: List[Workspace]) -> None:
    _ensure_dirs()
    from .encryption import write_json_file, get_session_password
    data = [
        {
            'id': ws.id,
            'name': ws.name,
            'accent': ws.accent,
            'bg_color': ws.bg_color,
            'services': [_service_to_dict(svc) for svc in ws.services],
            'groups': [_group_to_dict(g) for g in ws.groups],
        }
        for ws in workspaces
    ]
    write_json_file(_WORKSPACES_FILE, data, password=get_session_password())

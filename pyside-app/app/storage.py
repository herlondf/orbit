from __future__ import annotations

import json
import os
from typing import List

from .models import Account, Service, ServiceGroup, Workspace

_APPDATA = os.environ.get('APPDATA', os.path.expanduser('~'))
STORAGE_DIR = os.path.join(_APPDATA, 'Orbit')
STORAGE_FILE = os.path.join(STORAGE_DIR, 'workspace.json')
PROFILES_DIR = os.path.join(STORAGE_DIR, 'profiles')
_WORKSPACES_FILE = os.path.join(STORAGE_DIR, 'workspaces.json')


def _ensure_dirs() -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)


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
        'proxy': svc.proxy,
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
        proxy=s.get('proxy', ''),
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
                    result.append(Workspace(id=w['id'], name=w['name'], services=services, groups=groups, accent=w.get('accent', '')))
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
            'services': [_service_to_dict(svc) for svc in ws.services],
            'groups': [_group_to_dict(g) for g in ws.groups],
        }
        for ws in workspaces
    ]
    write_json_file(_WORKSPACES_FILE, data, password=get_session_password())

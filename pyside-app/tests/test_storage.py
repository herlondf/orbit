"""Tests for app.storage — settings, workspaces, shortcuts persistence."""
import json
import pytest


def test_save_load_settings_roundtrip(tmp_appdata):
    from app.storage import save_settings, load_settings
    data = {'theme': 'dark', 'sidebar_compact': True, 'count': 42}
    save_settings(data)
    loaded = load_settings()
    assert loaded == data


def test_load_settings_missing_file(tmp_appdata):
    from app.storage import load_settings
    result = load_settings()
    assert result == {}


def test_save_load_settings_overwrites(tmp_appdata):
    from app.storage import save_settings, load_settings
    save_settings({'a': 1})
    save_settings({'b': 2})
    loaded = load_settings()
    assert loaded == {'b': 2}


def test_service_to_dict_all_fields(sample_service):
    from app.storage import _service_to_dict
    d = _service_to_dict(sample_service)
    assert d['id'] == 'svc1'
    assert d['service_type'] == 'slack'
    assert d['name'] == 'Slack Test'
    assert d['icon'] == 'SL'
    assert d['color'] == '#4A154B'
    assert d['unread'] == 0
    assert d['hibernate_after'] is None
    assert d['pinned'] is False
    assert d['custom_css'] == ''
    assert d['custom_js'] == ''
    assert d['zoom'] == 1.0
    assert d['notification_sound'] == ''
    assert d['incognito'] is False
    assert d['proxy'] == ''
    assert len(d['accounts']) == 1
    assert d['accounts'][0]['id'] == 'acc1'


def test_service_from_dict_all_fields():
    from app.storage import _service_from_dict
    d = {
        'id': 's1', 'service_type': 'gmail', 'name': 'Gmail', 'icon': 'GM', 'color': '#red',
        'unread': 3, 'hibernate_after': 60, 'pinned': True,
        'custom_css': 'body{color:red}', 'custom_js': 'console.log(1)',
        'zoom': 1.25, 'notification_sound': 'bell', 'incognito': True, 'proxy': 'socks5://127.0.0.1:1080',
        'accounts': [{
            'id': 'a1', 'label': 'Work', 'url': 'https://mail.google.com',
            'profile_name': 'p1', 'notifications': 'muted', 'authuser': 1,
        }]
    }
    svc = _service_from_dict(d)
    assert svc.id == 's1'
    assert svc.service_type == 'gmail'
    assert svc.unread == 3
    assert svc.hibernate_after == 60
    assert svc.pinned is True
    assert svc.custom_css == 'body{color:red}'
    assert svc.custom_js == 'console.log(1)'
    assert svc.zoom == 1.25
    assert svc.notification_sound == 'bell'
    assert svc.incognito is True
    assert svc.proxy == 'socks5://127.0.0.1:1080'
    assert len(svc.accounts) == 1
    assert svc.accounts[0].authuser == 1
    assert svc.accounts[0].notifications == 'muted'


def test_service_from_dict_defaults():
    from app.storage import _service_from_dict
    d = {'id': 's1', 'name': 'X', 'icon': 'X', 'color': '#fff', 'accounts': []}
    svc = _service_from_dict(d)
    assert svc.service_type == 's1'  # falls back to id
    assert svc.unread == 0
    assert svc.pinned is False
    assert svc.incognito is False
    assert svc.proxy == ''
    assert svc.zoom == 1.0


def test_save_load_workspaces_roundtrip(tmp_appdata, sample_workspace):
    from app.storage import save_workspaces, load_workspaces
    save_workspaces([sample_workspace])
    loaded = load_workspaces()
    assert len(loaded) == 1
    ws = loaded[0]
    assert ws.id == 'ws1'
    assert ws.name == 'Main'
    assert len(ws.services) == 1
    svc = ws.services[0]
    assert svc.id == 'svc1'
    assert svc.service_type == 'slack'
    assert len(svc.accounts) == 1
    assert svc.accounts[0].id == 'acc1'


def test_save_load_workspaces_all_service_fields(tmp_appdata):
    from app.models import Account, Service, Workspace
    from app.storage import save_workspaces, load_workspaces
    acc = Account(id='a1', label='L', url='https://slack.com', profile_name='p1',
                  notifications='muted', authuser=2)
    svc = Service(
        id='s1', service_type='slack', name='Slack', icon='SL', color='#4A154B',
        accounts=[acc], unread=5, hibernate_after=30, pinned=True,
        custom_css='body{}', custom_js='var x=1', zoom=1.5,
        notification_sound='ding', incognito=True, proxy='http://p:8080',
    )
    ws = Workspace(id='ws1', name='Work', services=[svc])
    save_workspaces([ws])
    loaded = load_workspaces()
    s = loaded[0].services[0]
    assert s.unread == 5
    assert s.hibernate_after == 30
    assert s.pinned is True
    assert s.custom_css == 'body{}'
    assert s.custom_js == 'var x=1'
    assert s.zoom == 1.5
    assert s.notification_sound == 'ding'
    assert s.incognito is True
    assert s.proxy == 'http://p:8080'
    assert s.accounts[0].authuser == 2
    assert s.accounts[0].notifications == 'muted'


def test_save_load_workspaces_with_groups(tmp_appdata):
    from app.models import Service, Workspace, ServiceGroup, Account
    from app.storage import save_workspaces, load_workspaces
    acc = Account(id='a1', label='L', url='u', profile_name='p1')
    svc = Service(id='s1', service_type='slack', name='Slack', icon='SL', color='#fff', accounts=[acc])
    g = ServiceGroup(id='g1', name='Dev', service_ids=['s1'], collapsed=True)
    ws = Workspace(id='ws1', name='Main', services=[svc], groups=[g])
    save_workspaces([ws])
    loaded = load_workspaces()
    assert len(loaded[0].groups) == 1
    grp = loaded[0].groups[0]
    assert grp.id == 'g1'
    assert grp.name == 'Dev'
    assert grp.service_ids == ['s1']
    assert grp.collapsed is True


def test_load_workspaces_old_format_no_groups(tmp_appdata):
    """Old format without groups field → groups defaults to []."""
    import app.storage as storage_mod
    old_data = [{'id': 'ws1', 'name': 'Old', 'services': []}]
    with open(storage_mod._WORKSPACES_FILE, 'w') as f:
        json.dump(old_data, f)
    loaded = load_workspaces()
    assert loaded[0].groups == []


def test_load_workspaces_empty_file(tmp_appdata):
    """Empty / missing workspaces file → default workspace."""
    from app.storage import load_workspaces
    result = load_workspaces()
    assert len(result) == 1
    assert result[0].id == 'ws-default'


def test_load_shortcuts_defaults(tmp_appdata):
    from app.storage import load_shortcuts
    shortcuts = load_shortcuts()
    assert shortcuts['focus_mode'] == 'Ctrl+B'
    assert shortcuts['palette'] == 'Ctrl+K'
    assert shortcuts['dnd_toggle'] == 'Ctrl+D'
    assert shortcuts['quick_switch'] == 'Alt+`'


def test_save_load_shortcuts_roundtrip(tmp_appdata):
    from app.storage import load_shortcuts, save_shortcuts
    custom = {'focus_mode': 'Ctrl+Shift+B', 'palette': 'Ctrl+P'}
    save_shortcuts(custom)
    loaded = load_shortcuts()
    assert loaded['focus_mode'] == 'Ctrl+Shift+B'
    assert loaded['palette'] == 'Ctrl+P'
    # defaults still present for keys not overridden
    assert 'dnd_toggle' in loaded


def test_multiple_workspaces(tmp_appdata):
    from app.models import Workspace
    from app.storage import save_workspaces, load_workspaces
    ws1 = Workspace(id='ws1', name='Work')
    ws2 = Workspace(id='ws2', name='Personal')
    save_workspaces([ws1, ws2])
    loaded = load_workspaces()
    assert len(loaded) == 2
    assert {w.id for w in loaded} == {'ws1', 'ws2'}


def load_workspaces():
    from app.storage import load_workspaces as _lw
    return _lw()

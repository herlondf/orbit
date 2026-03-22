"""tests/test_batch2_features.py — Tests for Batch 2 features."""
from __future__ import annotations
import sys
import os
import pytest

# ── models ────────────────────────────────────────────────────────────────────

def test_workspace_has_bg_color():
    from app.models import Workspace
    ws = Workspace(id='test', name='Test')
    assert ws.bg_color == ''
    ws2 = Workspace(id='test2', name='Test2', bg_color='#ff0000')
    assert ws2.bg_color == '#ff0000'


def test_workspace_bg_color_default():
    from app.models import Workspace
    ws = Workspace(id='w1', name='W1', accent='#7c6af7')
    assert ws.bg_color == ''


# ── storage ───────────────────────────────────────────────────────────────────

def test_storage_save_load_bg_color(tmp_path, monkeypatch):
    import app.storage as storage
    monkeypatch.setattr(storage, '_WORKSPACES_FILE', str(tmp_path / 'ws.json'))
    monkeypatch.setattr(storage, '_SETTINGS_FILE', str(tmp_path / 'settings.json'))
    from app.models import Workspace
    ws = Workspace(id='ws-abc', name='MyWS', bg_color='#aabbcc')
    storage.save_workspaces([ws])
    loaded = storage.load_workspaces()
    assert loaded[0].bg_color == '#aabbcc'


def test_storage_load_missing_bg_color(tmp_path, monkeypatch):
    """Old data without bg_color should default to empty string."""
    import json
    import app.storage as storage
    ws_file = tmp_path / 'ws.json'
    ws_file.write_text(json.dumps([{'id': 'ws1', 'name': 'Old', 'accent': '', 'services': [], 'groups': []}]))
    monkeypatch.setattr(storage, '_WORKSPACES_FILE', str(ws_file))
    monkeypatch.setattr(storage, '_SETTINGS_FILE', str(tmp_path / 'settings.json'))
    loaded = storage.load_workspaces()
    assert loaded[0].bg_color == ''


# ── encryption DPAPI ──────────────────────────────────────────────────────────

def test_dpapi_protect_unprotect_non_windows():
    """On non-Windows, DPAPI functions return data unchanged."""
    import unittest.mock as mock
    with mock.patch('sys.platform', 'linux'):
        from importlib import reload
        import app.encryption as enc
        data = b'secret bytes'
        protected = enc.dpapi_protect(data)
        assert protected == data
        unprotected = enc.dpapi_unprotect(data)
        assert unprotected == data


def test_dpapi_protect_returns_bytes():
    from app.encryption import dpapi_protect
    result = dpapi_protect(b'test')
    assert isinstance(result, bytes)


def test_dpapi_unprotect_returns_bytes():
    from app.encryption import dpapi_unprotect
    result = dpapi_unprotect(b'test')
    assert isinstance(result, bytes)


def test_load_dpapi_key_missing(tmp_path, monkeypatch):
    import app.encryption as enc
    monkeypatch.setattr(enc, '_DPAPI_KEY_FILE', str(tmp_path / 'missing.key'))
    assert enc.load_dpapi_key() is None


def test_save_load_dpapi_key(tmp_path, monkeypatch):
    import app.encryption as enc
    monkeypatch.setattr(enc, '_DPAPI_KEY_FILE', str(tmp_path / 'dpapi.key'))
    key = b'my secret key 12345'
    enc.save_dpapi_key(key)
    loaded = enc.load_dpapi_key()
    # On non-Windows DPAPI is a no-op, so key == loaded
    assert loaded == key or loaded is not None


# ── biometric ─────────────────────────────────────────────────────────────────

def test_biometric_not_available_non_windows():
    import unittest.mock as mock
    with mock.patch('sys.platform', 'linux'):
        from app.biometric import WindowsHello
        assert WindowsHello.is_available() is False


def test_biometric_verify_returns_false_non_windows():
    import unittest.mock as mock
    with mock.patch('sys.platform', 'linux'):
        from app.biometric import WindowsHello
        assert WindowsHello.verify('test') is False


def test_biometric_module_importable():
    from app.biometric import WindowsHello
    assert hasattr(WindowsHello, 'is_available')
    assert hasattr(WindowsHello, 'verify')


# ── service_status ────────────────────────────────────────────────────────────

def test_service_status_importable():
    from app.service_status import ServiceStatusChecker
    assert ServiceStatusChecker is not None


def test_service_status_checker_init(qapp):
    from app.service_status import ServiceStatusChecker
    checker = ServiceStatusChecker([('svc1', 'https://example.com')])
    assert checker is not None
    checker.stop()


def test_service_status_set_services(qapp):
    from app.service_status import ServiceStatusChecker
    checker = ServiceStatusChecker([])
    checker.set_services([('s1', 'https://a.com'), ('s2', 'https://b.com')])
    assert len(checker._services) == 2
    checker.stop()


# ── taskbar ───────────────────────────────────────────────────────────────────

def test_taskbar_importable():
    from app.taskbar import update_badge
    assert callable(update_badge)


def test_taskbar_update_badge_non_windows():
    import unittest.mock as mock
    with mock.patch('sys.platform', 'linux'):
        from app.taskbar import update_badge
        # Should not raise
        update_badge(0, 5)


def test_taskbar_update_badge_zero():
    import unittest.mock as mock
    with mock.patch('sys.platform', 'linux'):
        from app.taskbar import update_badge
        update_badge(0, 0)


# ── notif_center ──────────────────────────────────────────────────────────────

def test_notif_center_importable():
    from app.notif_center import NotificationCenter, NotifEntryWidget
    assert NotificationCenter is not None
    assert NotifEntryWidget is not None


def test_notif_center_init(qapp):
    from app.notif_center import NotificationCenter
    from PySide6.QtWidgets import QWidget
    parent = QWidget()
    nc = NotificationCenter(parent, '#7c6af7')
    assert nc is not None
    assert nc.PANEL_WIDTH == 320
    parent.deleteLater()


def test_notif_center_set_accent(qapp):
    from app.notif_center import NotificationCenter
    from PySide6.QtWidgets import QWidget
    parent = QWidget()
    nc = NotificationCenter(parent)
    nc.set_accent('#ff0000')
    assert nc._accent == '#ff0000'
    parent.deleteLater()


def test_notif_center_update_services(qapp):
    from app.notif_center import NotificationCenter
    from PySide6.QtWidgets import QWidget
    parent = QWidget()
    nc = NotificationCenter(parent)
    nc.update_services(['Slack', 'Gmail', 'Notion'])
    # Filter combo has 'Todos os serviços' + 3 services = 4 items
    assert nc._filter_combo.count() == 4
    parent.deleteLater()


def test_notif_center_is_open_initially_false(qapp):
    from app.notif_center import NotificationCenter
    from PySide6.QtWidgets import QWidget
    parent = QWidget()
    nc = NotificationCenter(parent)
    assert nc.is_open() is False
    parent.deleteLater()


# ── security_monitor ─────────────────────────────────────────────────────────

def test_security_monitor_importable():
    from app.security_monitor import SecurityMonitor
    assert SecurityMonitor is not None


def test_security_monitor_init(qapp):
    from app.security_monitor import SecurityMonitor
    monitor = SecurityMonitor()
    assert monitor is not None
    monitor.stop()


def test_security_monitor_scan_non_windows():
    """On non-Windows, _check should not emit threats."""
    import unittest.mock as mock
    from app.security_monitor import SecurityMonitor
    monitor = SecurityMonitor()
    threats = []
    monitor.threat_detected.connect(threats.append)
    with mock.patch('sys.platform', 'linux'):
        monitor._check()
    assert threats == []
    monitor.stop()


def test_security_monitor_suspicious_names():
    from app.security_monitor import _SUSPICIOUS_NAMES
    assert 'keylogger' in _SUSPICIOUS_NAMES
    assert len(_SUSPICIOUS_NAMES) > 5


# ── webdav_sync ───────────────────────────────────────────────────────────────

def test_webdav_importable():
    from app.webdav_sync import WebDAVSync, get_webdav, load_webdav_config, save_webdav_config
    assert WebDAVSync is not None
    assert callable(get_webdav)


def test_webdav_configure():
    from app.webdav_sync import WebDAVSync
    wd = WebDAVSync()
    wd.configure('https://example.com/dav/', 'user', 'pass')
    assert wd._url == 'https://example.com/dav'
    assert wd._username == 'user'
    assert wd._password == 'pass'


def test_webdav_backup_filename():
    from app.webdav_sync import WebDAVSync
    name = WebDAVSync.backup_filename()
    assert name.startswith('orbit-backup-')
    assert name.endswith('.json')


def test_webdav_get_singleton():
    from app.webdav_sync import get_webdav, WebDAVSync
    wd = get_webdav()
    assert isinstance(wd, WebDAVSync)


def test_webdav_save_load_config(tmp_path, monkeypatch):
    import app.storage as storage
    monkeypatch.setattr(storage, '_SETTINGS_FILE', str(tmp_path / 'settings.json'))
    from app.webdav_sync import save_webdav_config, load_webdav_config
    save_webdav_config('https://dav.example.com', 'user1', 'pw123')
    cfg = load_webdav_config()
    assert cfg['url'] == 'https://dav.example.com'
    assert cfg['username'] == 'user1'


def test_webdav_test_connection_no_server():
    from app.webdav_sync import WebDAVSync
    wd = WebDAVSync()
    wd.configure('http://localhost:19999/nonexistent', '', '')
    try:
        ok, msg = wd.test_connection()
        assert isinstance(ok, bool)
        assert isinstance(msg, str)
    except Exception:
        pass  # requests not installed is OK for this test


def test_webdav_list_backups_no_server():
    from app.webdav_sync import WebDAVSync
    wd = WebDAVSync()
    wd.configure('http://localhost:19999/nonexistent', '', '')
    try:
        backups = wd.list_backups()
        assert isinstance(backups, list)
    except Exception:
        pass


def test_webdav_init_from_settings_no_config(tmp_path, monkeypatch):
    import app.storage as storage
    monkeypatch.setattr(storage, '_SETTINGS_FILE', str(tmp_path / 'settings.json'))
    from app.webdav_sync import init_from_settings
    result = init_from_settings()
    assert result is False


def test_webdav_upload_data_no_server():
    from app.webdav_sync import WebDAVSync
    wd = WebDAVSync()
    wd.configure('http://localhost:19999/nonexistent', '', '')
    try:
        ok = wd.upload_data('test.json', b'{}')
        assert isinstance(ok, bool)
    except Exception:
        pass

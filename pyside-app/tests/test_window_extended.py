"""Extended tests for app.window — covering business logic methods."""
import sys
import time
import pytest
from unittest.mock import patch, MagicMock

win32_only = pytest.mark.skipif(sys.platform != 'win32', reason='Windows only')


@pytest.fixture(autouse=True)
def patch_storage_for_window_ext(tmp_appdata):
    """Ensure window tests use temp storage with onboarding done."""
    from app.storage import save_settings, save_workspaces
    from app.models import Workspace
    save_settings({'onboarding_done': True, 'sidebar_compact': False})
    save_workspaces([Workspace(id='ws-default', name='Main', services=[])])


@pytest.fixture
def window(qtbot, patch_storage_for_window_ext):
    from app.window import OrbitWindow
    win = OrbitWindow()
    qtbot.addWidget(win)
    return win


# ── _until_tomorrow_minutes (line 2528-2531) ──────────────────────────────────

def test_until_tomorrow_minutes_returns_positive(window):
    minutes = window._until_tomorrow_minutes()
    assert minutes >= 1


def test_until_tomorrow_minutes_is_int(window):
    minutes = window._until_tomorrow_minutes()
    assert isinstance(minutes, int)


def test_until_tomorrow_minutes_max_is_1440(window):
    minutes = window._until_tomorrow_minutes()
    # Max possible is ~24h = 1440 minutes (actually ~16h until 8am tomorrow)
    assert minutes <= 1440


# ── _is_startup_enabled (lines 3248-3249) ─────────────────────────────────────

@win32_only
def test_is_startup_enabled_returns_bool(window):
    result = window._is_startup_enabled()
    assert isinstance(result, bool)


@win32_only
def test_is_startup_enabled_winreg_not_found(window):
    import winreg
    with patch('winreg.OpenKey', side_effect=FileNotFoundError('not found')):
        result = window._is_startup_enabled()
    assert result is False


@win32_only
def test_is_startup_enabled_winreg_success(window):
    with patch('winreg.OpenKey') as mock_open, \
         patch('winreg.QueryValueEx') as mock_query, \
         patch('winreg.CloseKey'):
        mock_query.return_value = ('value', 1)
        result = window._is_startup_enabled()
    assert result is True


# ── _set_startup (lines 3254-3271) ────────────────────────────────────────────

@win32_only
def test_set_startup_enable_calls_winreg(window):
    with patch('winreg.OpenKey') as mock_open, \
         patch('winreg.SetValueEx') as mock_set, \
         patch('winreg.CloseKey'):
        mock_open.return_value = MagicMock()
        window._set_startup(True)
    mock_set.assert_called_once()


@win32_only
def test_set_startup_disable_calls_delete(window):
    mock_key = MagicMock()
    with patch('winreg.OpenKey', return_value=mock_key), \
         patch('winreg.DeleteValue') as mock_del, \
         patch('winreg.CloseKey'):
        window._set_startup(False)
    mock_del.assert_called_once()


@win32_only
def test_set_startup_handles_exception(window):
    with patch('winreg.OpenKey', side_effect=PermissionError('denied')):
        # Should not raise
        window._set_startup(True)


@win32_only
def test_set_startup_handles_delete_not_found(window):
    mock_key = MagicMock()
    with patch('winreg.OpenKey', return_value=mock_key), \
         patch('winreg.DeleteValue', side_effect=FileNotFoundError()), \
         patch('winreg.CloseKey'):
        window._set_startup(False)  # Should not raise


# ── _switch_workspace (lines 1298-1321) ───────────────────────────────────────

def test_switch_workspace_same_id_is_noop(window):
    """Switching to the same workspace does nothing."""
    from app.models import Workspace
    ws = window._active_workspace
    original_services = window._services[:]
    with patch.object(window, '_rebuild_sidebar') as mock_rebuild:
        window._switch_workspace(ws)
    mock_rebuild.assert_not_called()


def test_switch_workspace_changes_active(window):
    """Switching to a different workspace updates _active_workspace."""
    from app.models import Workspace
    ws2 = Workspace(id='ws-other', name='Other', services=[])
    window._workspaces = [window._active_workspace, ws2]
    with patch.object(window, '_rebuild_sidebar'), \
         patch.object(window, '_update_workspace_btn'), \
         patch.object(window, '_refresh_header'), \
         patch.object(window, '_update_title_badge'), \
         patch.object(window, '_select_service'):
        window._switch_workspace(ws2)
    assert window._active_workspace.id == 'ws-other'


def test_switch_workspace_updates_services(window):
    """Switching workspace updates _services."""
    from app.models import Workspace, Service, Account
    acc = Account(id='a1', label='L', url='https://example.com', profile_name='p1')
    svc = Service(id='s1', service_type='slack', name='Slack',
                  icon='SL', color='#4A154B', accounts=[acc])
    ws2 = Workspace(id='ws-other', name='Other', services=[svc])
    window._workspaces = [window._active_workspace, ws2]
    with patch.object(window, '_rebuild_sidebar'), \
         patch.object(window, '_update_workspace_btn'), \
         patch.object(window, '_refresh_header'), \
         patch.object(window, '_update_title_badge'), \
         patch.object(window, '_select_service'):
        window._switch_workspace(ws2)
    assert len(window._services) == 1
    assert window._services[0].id == 's1'


# ── handle_url_scheme (lines 3395-3418) ───────────────────────────────────────

def test_handle_url_scheme_open(window):
    """orbit://open brings window to front."""
    with patch.object(window, 'show') as mock_show, \
         patch.object(window, 'raise_') as mock_raise, \
         patch.object(window, 'activateWindow') as mock_activate:
        window.handle_url_scheme('orbit://open')
    mock_show.assert_called_once()
    mock_raise.assert_called_once()


def test_handle_url_scheme_service(window):
    """orbit://service/<id> calls _select_service."""
    from app.models import Service, Account
    acc = Account(id='a1', label='L', url='https://example.com', profile_name='p1')
    svc = Service(id='svc-123', service_type='slack', name='MySlack',
                  icon='SL', color='#4A154B', accounts=[acc])
    window._services = [svc]
    with patch.object(window, 'show'), patch.object(window, 'raise_'), \
         patch.object(window, 'activateWindow'), \
         patch.object(window, '_select_service') as mock_select:
        window.handle_url_scheme('orbit://service/svc-123')
    mock_select.assert_called_once_with(svc)


def test_handle_url_scheme_workspace(window):
    """orbit://workspace/<name> calls _switch_workspace."""
    from app.models import Workspace
    ws2 = Workspace(id='ws-work', name='Work', services=[])
    window._workspaces = [window._active_workspace, ws2]
    with patch.object(window, 'show'), patch.object(window, 'raise_'), \
         patch.object(window, 'activateWindow'), \
         patch.object(window, '_switch_workspace') as mock_switch:
        window.handle_url_scheme('orbit://workspace/Work')
    mock_switch.assert_called_once_with(ws2)


def test_handle_url_scheme_unknown_command(window):
    """Unknown orbit:// command does not crash."""
    with patch.object(window, 'show'), patch.object(window, 'raise_'), \
         patch.object(window, 'activateWindow'):
        window.handle_url_scheme('orbit://unknowncommand')


def test_handle_url_scheme_empty_path(window):
    """orbit:// with no path is handled gracefully."""
    with patch.object(window, 'show'), patch.object(window, 'raise_'), \
         patch.object(window, 'activateWindow'):
        window.handle_url_scheme('orbit://')


def test_handle_url_scheme_exception_handled(window):
    """handle_url_scheme handles internal exception gracefully."""
    with patch.object(window, 'show'), patch.object(window, 'raise_'), \
         patch.object(window, 'activateWindow'):
        # Trigger exception path by making _workspaces inaccessible
        original = window._workspaces
        del window._workspaces
        try:
            window.handle_url_scheme('orbit://workspace/SomeName')
        finally:
            window._workspaces = original
    """orbit://service/<name> matches service by name (case-insensitive)."""
    from app.models import Service, Account
    acc = Account(id='a1', label='L', url='https://example.com', profile_name='p1')
    svc = Service(id='svc-xyz', service_type='slack', name='My Slack',
                  icon='SL', color='#4A154B', accounts=[acc])
    window._services = [svc]
    with patch.object(window, 'show'), patch.object(window, 'raise_'), \
         patch.object(window, 'activateWindow'), \
         patch.object(window, '_select_service') as mock_select:
        window.handle_url_scheme('orbit://service/my slack')
    mock_select.assert_called_once_with(svc)

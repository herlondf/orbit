"""Tests for app.window — OrbitWindow (smoke tests with mocking)."""
import time
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def patch_storage_for_window(tmp_appdata):
    """Ensure window tests use temp storage with onboarding done."""
    from app.storage import save_settings, save_workspaces
    from app.models import Workspace
    save_settings({'onboarding_done': True, 'sidebar_compact': False})
    save_workspaces([Workspace(id='ws-default', name='Main', services=[])])


@pytest.fixture
def window(qtbot, patch_storage_for_window):
    """Create OrbitWindow — empty workspace means no ServiceView is created."""
    from app.window import OrbitWindow
    win = OrbitWindow()
    qtbot.addWidget(win)
    return win


def test_window_instantiates(qtbot, patch_storage_for_window):
    """OrbitWindow can be created without error when onboarding is done."""
    from app.window import OrbitWindow
    win = OrbitWindow()
    qtbot.addWidget(win)
    assert win is not None


def test_dnd_inactive_when_none(window):
    """_is_dnd_active returns False when _dnd_until is None."""
    window._dnd_until = None
    with patch('app.window.load_settings', return_value={'quiet_hours': {'enabled': False}}):
        assert window._is_dnd_active() is False


def test_dnd_active_when_future(window):
    """_is_dnd_active returns True when _dnd_until is in the future."""
    window._dnd_until = time.time() + 3600  # 1 hour from now
    assert window._is_dnd_active() is True


def test_dnd_inactive_when_past(window):
    """_is_dnd_active returns False when _dnd_until is in the past."""
    window._dnd_until = time.time() - 1  # 1 second ago
    with patch('app.window.load_settings', return_value={'quiet_hours': {'enabled': False}}):
        assert window._is_dnd_active() is False


def test_select_service_by_id_nonexistent(window):
    """_select_service_by_id with unknown id does not crash."""
    window._select_service_by_id('nonexistent-service-id-xyz')


def test_toggle_compact_toggles_state(window, tmp_appdata):
    """_toggle_compact toggles _sidebar_compact and saves."""
    initial = window._sidebar_compact
    with patch.object(window, '_rebuild_sidebar'):
        window._toggle_compact()
    assert window._sidebar_compact == (not initial)


def test_toggle_compact_saves_setting(window, tmp_appdata):
    """_toggle_compact persists the new value to settings."""
    from app.storage import load_settings
    with patch.object(window, '_rebuild_sidebar'):
        window._toggle_compact()
    saved = load_settings()
    assert 'sidebar_compact' in saved
    assert saved['sidebar_compact'] == window._sidebar_compact


def test_toggle_compact_twice_restores(window, tmp_appdata):
    """Toggling compact twice returns to original state."""
    initial = window._sidebar_compact
    with patch.object(window, '_rebuild_sidebar'):
        window._toggle_compact()
        window._toggle_compact()
    assert window._sidebar_compact == initial

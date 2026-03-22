import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def tmp_appdata(tmp_path, monkeypatch):
    """Redirect APPDATA and all module-level paths to a temp directory."""
    monkeypatch.setenv('APPDATA', str(tmp_path))

    storage_dir = tmp_path / 'Orbit'
    storage_dir.mkdir(parents=True, exist_ok=True)

    import app.storage as storage_mod
    monkeypatch.setattr(storage_mod, 'STORAGE_DIR', str(storage_dir))
    monkeypatch.setattr(storage_mod, 'STORAGE_FILE', str(storage_dir / 'workspace.json'))
    monkeypatch.setattr(storage_mod, '_WORKSPACES_FILE', str(storage_dir / 'workspaces.json'))
    monkeypatch.setattr(storage_mod, '_SETTINGS_FILE', str(storage_dir / 'settings.json'))

    import app.stats as stats_mod
    monkeypatch.setattr(stats_mod, '_STATS_FILE', str(storage_dir / 'stats.json'))
    monkeypatch.setattr(stats_mod, 'STORAGE_DIR', str(storage_dir))

    import app.notif_history as nh_mod
    from pathlib import Path
    monkeypatch.setattr(nh_mod, 'HISTORY_FILE', Path(storage_dir) / 'notif_history.json')
    nh_mod._history.clear()

    return tmp_path


@pytest.fixture
def sample_account():
    from app.models import Account
    return Account(id='acc1', label='Test Account', url='https://example.com', profile_name='prof1')


@pytest.fixture
def sample_service(sample_account):
    from app.models import Service
    return Service(
        id='svc1', service_type='slack', name='Slack Test',
        icon='SL', color='#4A154B', accounts=[sample_account]
    )


@pytest.fixture
def sample_workspace(sample_service):
    from app.models import Workspace
    return Workspace(id='ws1', name='Main', services=[sample_service])

import gc
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Suppress all real system tray notifications during tests
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Prevent QtWebEngine GPU crash in headless CI
os.environ.setdefault(
    'QTWEBENGINE_CHROMIUM_FLAGS',
    '--no-sandbox --disable-gpu --disable-software-rasterizer'
)
os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')
os.environ.setdefault('QT_OPENGL', 'software')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ---------------------------------------------------------------------------
# Stub QWebEngineView with a plain QWidget so no Chromium process is spawned.
# This prevents segfaults on Linux CI during teardown.
# ---------------------------------------------------------------------------
try:
    from PySide6.QtWidgets import QWidget
    import PySide6.QtWebEngineWidgets as _qwev

    class _StubWebEngineView(QWidget):
        """Lightweight stand-in for QWebEngineView — no Chromium subprocess."""
        def load(self, *a): pass
        def setUrl(self, *a): pass
        def setHtml(self, *a, **kw): pass
        def page(self): return MagicMock()
        def settings(self): return MagicMock()
        def setZoomFactor(self, *a): pass
        def zoomFactor(self): return 1.0
        def back(self): pass
        def forward(self): pass
        def reload(self): pass
        def stop(self): pass
        def history(self): return MagicMock()
        def title(self): return ''
        def url(self): return MagicMock()
        def findText(self, *a, **kw): pass
        def runJavaScript(self, *a, **kw): pass
        def setPage(self, *a): pass
        def loadStarted(self): pass
        def loadFinished(self): pass
        def titleChanged(self): pass
        def urlChanged(self): pass

    _qwev.QWebEngineView = _StubWebEngineView
except Exception:
    pass


@pytest.fixture(autouse=True)
def _suppress_tray_notifications(monkeypatch):
    """Prevent QSystemTrayIcon.showMessage from firing real OS notifications."""
    try:
        from PySide6.QtWidgets import QSystemTrayIcon
        monkeypatch.setattr(QSystemTrayIcon, 'showMessage', lambda *a, **kw: None)
        monkeypatch.setattr(QSystemTrayIcon, 'show', lambda *a, **kw: None)
    except Exception:
        pass


@pytest.fixture(scope='session', autouse=True)
def _qt_session_cleanup(qapp):
    """Session-level cleanup: flush Qt events after all tests to prevent crashes."""
    yield
    for _ in range(3):
        try:
            qapp.processEvents()
            gc.collect()
        except Exception:
            break


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

"""Tests for app.webview — make_profile, set_ad_block."""
import pytest


def test_set_ad_block_true():
    from app.webview import set_ad_block, _ad_block_enabled
    import app.webview as wv
    set_ad_block(True)
    assert wv._ad_block_enabled is True


def test_set_ad_block_false():
    from app.webview import set_ad_block
    import app.webview as wv
    set_ad_block(False)
    assert wv._ad_block_enabled is False
    set_ad_block(True)  # restore


def test_user_agent_string():
    from app.webview import USER_AGENT
    assert 'Mozilla' in USER_AGENT
    assert 'Chrome' in USER_AGENT
    assert 'Windows' in USER_AGENT


def test_chrome_version_constant():
    from app.webview import _CHROME_VER
    assert _CHROME_VER.isdigit()
    assert int(_CHROME_VER) >= 100


def test_make_profile_incognito(qtbot, tmp_path, monkeypatch):
    """Test make_profile() with incognito=True."""
    from app.webview import make_profile
    import app.storage as storage_mod
    monkeypatch.setattr(storage_mod, 'PROFILES_DIR', str(tmp_path / 'profiles'))

    import app.webview as wv
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))

    profile = make_profile('test-incognito', incognito=True)
    assert profile is not None
    # Incognito profile should be off-the-record
    assert profile.isOffTheRecord()


def test_make_profile_persistent(qtbot, tmp_path, monkeypatch):
    """Test make_profile() with persistent storage."""
    from app.webview import make_profile
    import app.webview as wv
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))

    profile = make_profile('test-persistent-profile', incognito=False)
    assert profile is not None
    assert not profile.isOffTheRecord()


def test_make_profile_slack(qtbot, tmp_path, monkeypatch):
    """Test make_profile() with service_type='slack' (Slack UA path)."""
    from app.webview import make_profile
    import app.webview as wv
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))

    profile = make_profile('test-slack-profile', incognito=True, service_type='slack')
    assert profile is not None


def test_make_profile_default_service(qtbot, tmp_path, monkeypatch):
    """Test make_profile() with default (non-slack) service type."""
    from app.webview import make_profile
    import app.webview as wv
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))

    profile = make_profile('test-default-profile', incognito=True, service_type='gmail')
    assert profile is not None


def test_stealth_interceptor_instantiation(qtbot, tmp_path, monkeypatch):
    """Test _StealthInterceptor can be instantiated."""
    import app.webview as wv
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))

    from PySide6.QtWebEngineCore import QWebEngineProfile
    profile = QWebEngineProfile()
    interceptor = wv._StealthInterceptor(profile, 'TestUA', 'sec-ch-ua')
    assert interceptor is not None
    assert interceptor._ua == b'TestUA'


def test_google_types_constant():
    from app.webview import _GOOGLE_TYPES
    assert 'gmail' in _GOOGLE_TYPES
    assert 'gchat' in _GOOGLE_TYPES

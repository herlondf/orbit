"""Tests for _StealthInterceptor.interceptRequest — ad block + header injection."""
import pytest
from unittest.mock import MagicMock, patch


def test_interceptRequest_blocked_url(qtbot, tmp_path, monkeypatch):
    """interceptRequest blocks an ad domain URL when ad block is enabled."""
    import app.webview as wv
    from PySide6.QtWebEngineCore import QWebEngineProfile
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))
    monkeypatch.setattr(wv, '_ad_block_enabled', True)

    profile = QWebEngineProfile()
    interceptor = wv._StealthInterceptor(profile, 'TestUA', 'sec-ch-ua')

    # Mock request info
    mock_info = MagicMock()
    mock_info.requestUrl().toString.return_value = 'https://doubleclick.net/ads'

    interceptor.interceptRequest(mock_info)
    mock_info.block.assert_called_once_with(True)


def test_interceptRequest_allowed_url_sets_headers(qtbot, tmp_path, monkeypatch):
    """interceptRequest sets UA headers for allowed URLs."""
    import app.webview as wv
    from PySide6.QtWebEngineCore import QWebEngineProfile
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))
    monkeypatch.setattr(wv, '_ad_block_enabled', True)

    profile = QWebEngineProfile()
    interceptor = wv._StealthInterceptor(profile, 'TestUA', 'sec-ch-ua')

    mock_info = MagicMock()
    mock_info.requestUrl().toString.return_value = 'https://slack.com/api/v2'

    interceptor.interceptRequest(mock_info)
    mock_info.block.assert_not_called()
    # Should set headers
    assert mock_info.setHttpHeader.call_count >= 1


def test_interceptRequest_ad_block_disabled(qtbot, tmp_path, monkeypatch):
    """When ad block is disabled, headers are set for all URLs including ad domains."""
    import app.webview as wv
    from PySide6.QtWebEngineCore import QWebEngineProfile
    monkeypatch.setattr(wv, 'PROFILES_DIR', str(tmp_path / 'profiles'))
    monkeypatch.setattr(wv, '_ad_block_enabled', False)

    profile = QWebEngineProfile()
    interceptor = wv._StealthInterceptor(profile, 'TestUA', '')

    mock_info = MagicMock()
    mock_info.requestUrl().toString.return_value = 'https://doubleclick.net/ads'

    interceptor.interceptRequest(mock_info)
    # Should NOT block (ad block is disabled)
    mock_info.block.assert_not_called()
    # Should set headers
    assert mock_info.setHttpHeader.call_count >= 1

    # Restore
    monkeypatch.setattr(wv, '_ad_block_enabled', True)

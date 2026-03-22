"""Tests for Slack bridge compatibility layer."""
from __future__ import annotations

import pytest
from app.slack_bridge import (
    SLACK_ELECTRON_UA,
    SLACK_STEALTH_JS,
    SLACK_BLOCKED_OVERLAY_JS,
    SLACK_SEC_CH_UA,
    SLACK_APP_URL,
    is_slack_service,
    get_slack_ua,
    get_slack_sec_ch_ua,
)


def test_is_slack_service_true():
    assert is_slack_service('slack') is True
    assert is_slack_service('Slack') is True
    assert is_slack_service('SLACK') is True


def test_is_slack_service_false():
    assert is_slack_service('teams') is False
    assert is_slack_service('discord') is False
    assert is_slack_service('whatsapp') is False
    assert is_slack_service('') is False


def test_slack_ua_contains_electron():
    ua = get_slack_ua()
    assert 'Electron' in ua
    assert 'Slack' in ua
    assert 'Chrome' in ua
    assert 'Windows NT' in ua


def test_slack_ua_is_string():
    ua = get_slack_ua()
    assert isinstance(ua, str)
    assert len(ua) > 50


def test_slack_sec_ch_ua_format():
    sec_ch = get_slack_sec_ch_ua()
    assert 'Chromium' in sec_ch
    assert 'Google Chrome' in sec_ch
    assert 'Not?A_Brand' in sec_ch


def test_slack_stealth_js_contains_electron_globals():
    js = SLACK_STEALTH_JS
    assert 'window.process' in js
    assert 'window.require' in js
    assert 'ipcRenderer' in js
    assert 'electron' in js


def test_slack_stealth_js_removes_webdriver():
    js = SLACK_STEALTH_JS
    assert 'webdriver' in js


def test_slack_stealth_js_contains_client_hints():
    js = SLACK_STEALTH_JS
    assert 'userAgentData' in js
    assert 'getHighEntropyValues' in js


def test_slack_blocked_overlay_js():
    js = SLACK_BLOCKED_OVERLAY_JS
    assert 'orbit-slack-fallback' in js
    assert 'app.slack.com' in js


def test_slack_app_url():
    assert SLACK_APP_URL.startswith('https://')
    assert 'slack.com' in SLACK_APP_URL


def test_ua_differs_from_standard():
    """Slack UA should be different from the standard Chrome UA."""
    from app.webview import USER_AGENT
    assert get_slack_ua() != USER_AGENT


def test_slack_ua_version_numbers():
    """UA should contain version numbers in the right format."""
    ua = get_slack_ua()
    import re
    # Check Slack/X.Y.Z format
    assert re.search(r'Slack/\d+\.\d+\.\d+', ua), 'Missing Slack version'
    # Check Electron/X.Y.Z format
    assert re.search(r'Electron/\d+\.\d+\.\d+', ua), 'Missing Electron version'

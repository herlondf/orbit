"""Tests for app.adblocker — domain-based blocking logic."""
import pytest


def test_is_blocked_ad_domain():
    from app.adblocker import is_blocked
    assert is_blocked('https://doubleclick.net/ads') is True


def test_is_blocked_subdomain():
    from app.adblocker import is_blocked
    assert is_blocked('https://ad.doubleclick.net/pagead/ads') is True


def test_is_blocked_tracker():
    from app.adblocker import is_blocked
    assert is_blocked('https://googletagmanager.com/gtm.js') is True


def test_is_blocked_google_analytics():
    from app.adblocker import is_blocked
    assert is_blocked('https://google-analytics.com/analytics.js') is True


def test_is_blocked_legitimate_domain():
    from app.adblocker import is_blocked
    assert is_blocked('https://google.com') is False


def test_is_blocked_legitimate_subdomain():
    from app.adblocker import is_blocked
    assert is_blocked('https://mail.google.com/mail/u/0/') is False


def test_is_blocked_slack():
    from app.adblocker import is_blocked
    assert is_blocked('https://app.slack.com/client/') is False


def test_is_blocked_invalid_url():
    from app.adblocker import is_blocked
    # Should not raise, just return False
    result = is_blocked('not-a-url')
    assert isinstance(result, bool)


def test_is_blocked_empty_string():
    from app.adblocker import is_blocked
    assert is_blocked('') is False


def test_is_blocked_amazon_ads():
    from app.adblocker import is_blocked
    assert is_blocked('https://amazon-adsystem.com/e/dtb/bid') is True


def test_is_blocked_hotjar():
    from app.adblocker import is_blocked
    assert is_blocked('https://hotjar.com/api/v2/track') is True


def test_is_blocked_mixpanel():
    from app.adblocker import is_blocked
    assert is_blocked('https://mixpanel.com/track') is True


def test_block_domains_is_set():
    """Verify _BLOCK_DOMAINS contains expected entries."""
    from app.adblocker import _BLOCK_DOMAINS
    assert 'doubleclick.net' in _BLOCK_DOMAINS
    assert 'google-analytics.com' in _BLOCK_DOMAINS
    assert 'googletagmanager.com' in _BLOCK_DOMAINS


def test_is_blocked_with_path():
    """URL with path should still block based on domain."""
    from app.adblocker import is_blocked
    assert is_blocked('https://criteo.com/some/long/path?q=1') is True


def test_is_blocked_segment():
    from app.adblocker import is_blocked
    assert is_blocked('https://segment.io/v1/track') is True

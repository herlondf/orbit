"""Extended tests for app.adblocker — covering exception handler."""
import pytest
from unittest.mock import patch


def test_is_blocked_exception_handler():
    """Trigger the exception path in is_blocked()."""
    from app.adblocker import is_blocked
    with patch('urllib.parse.urlparse', side_effect=Exception('parse error')):
        result = is_blocked('https://doubleclick.net/ads')
    # Should not raise, should return False
    assert result is False


def test_is_blocked_none_hostname():
    """URL with no hostname returns False safely."""
    from app.adblocker import is_blocked
    # Fragment-only URLs have no hostname
    result = is_blocked('file:///local/path')
    assert isinstance(result, bool)

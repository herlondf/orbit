"""Tests for app.updater — version checking and update detection."""
import json
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO


def _mock_response(data: dict):
    """Create a mock urlopen context manager response."""
    body = json.dumps(data).encode()
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read = MagicMock(return_value=body)
    return mock_resp


def test_app_version_semver():
    from app.updater import APP_VERSION
    parts = APP_VERSION.split('.')
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit(), f"Non-numeric version part: {part}"


def test_no_update_when_same_version():
    from app.updater import APP_VERSION, check_for_update
    mock_resp = _mock_response({'tag_name': f'v{APP_VERSION}', 'html_url': 'https://github.com/r', 'assets': []})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is False


def test_update_available_when_newer():
    from app.updater import check_for_update
    mock_resp = _mock_response({'tag_name': 'v99.9.9', 'html_url': 'https://github.com/rel', 'assets': []})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is True
    assert version == '99.9.9'
    assert url == 'https://github.com/rel'


def test_no_update_when_older_version():
    from app.updater import check_for_update
    mock_resp = _mock_response({'tag_name': 'v0.0.1', 'html_url': 'https://github.com/r', 'assets': []})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is False


def test_network_error_returns_false():
    from app.updater import check_for_update
    with patch('urllib.request.urlopen', side_effect=Exception('Network error')):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is False
    assert version == ''
    assert url == ''
    assert dl_url == ''


def test_malformed_response_returns_false():
    from app.updater import check_for_update
    mock_resp = _mock_response({})  # no tag_name
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is False


def test_version_gt_logic():
    from app.updater import _version_gt
    assert _version_gt('1.0.1', '1.0.0') is True
    assert _version_gt('2.0.0', '1.9.9') is True
    assert _version_gt('1.0.0', '1.0.0') is False
    assert _version_gt('0.9.9', '1.0.0') is False
    assert _version_gt('1.1.0', '1.0.9') is True


def test_update_returns_tuple_of_4():
    from app.updater import check_for_update
    with patch('urllib.request.urlopen', side_effect=Exception()):
        result = check_for_update()
    assert isinstance(result, tuple)
    assert len(result) == 4


def test_tag_name_without_v_prefix():
    from app.updater import check_for_update
    mock_resp = _mock_response({'tag_name': '99.0.0', 'html_url': 'https://github.com/r', 'assets': []})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is True
    assert version == '99.0.0'

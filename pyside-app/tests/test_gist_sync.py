"""Tests for app.gist_sync — GitHub Gist API interactions."""
import json
import pytest
from unittest.mock import MagicMock, patch, call


def _make_response(data, status=200):
    """Create a mock urllib response context manager."""
    body = json.dumps(data).encode()
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read = MagicMock(return_value=body)
    mock_resp.status = status
    return mock_resp


def test_create_gist_returns_id():
    from app.gist_sync import create_gist
    mock_resp = _make_response({'id': 'abc123def456'})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        gist_id = create_gist('token123', '{"data": "test"}')
    assert gist_id == 'abc123def456'


def test_create_gist_sends_post():
    from app.gist_sync import create_gist
    mock_resp = _make_response({'id': 'xyz'})
    with patch('urllib.request.urlopen', return_value=mock_resp) as mock_open:
        with patch('urllib.request.Request') as mock_req:
            mock_req.return_value = MagicMock()
            create_gist('mytoken', 'content')
            args, kwargs = mock_req.call_args
            # method should be POST
            assert kwargs.get('method') == 'POST' or (len(args) >= 4 and args[3] == 'POST') or mock_req.call_args[1].get('method') == 'POST'


def test_create_gist_includes_auth_header():
    from app.gist_sync import create_gist, _headers
    headers = _headers('mytoken')
    assert headers['Authorization'] == 'token mytoken'


def test_update_gist_sends_patch():
    from app.gist_sync import update_gist
    mock_resp = _make_response({})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        with patch('urllib.request.Request') as mock_req:
            mock_req.return_value = MagicMock()
            update_gist('token', 'gist123', 'new content')
            _, kwargs = mock_req.call_args
            assert kwargs.get('method') == 'PATCH'


def test_update_gist_uses_correct_url():
    from app.gist_sync import update_gist, GIST_API
    mock_resp = _make_response({})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        with patch('urllib.request.Request') as mock_req:
            mock_req.return_value = MagicMock()
            update_gist('token', 'gist_xyz', 'content')
            args, _ = mock_req.call_args
            assert 'gist_xyz' in args[0]


def test_fetch_gist_returns_content():
    from app.gist_sync import fetch_gist
    mock_resp = _make_response({
        'files': {
            'Orbit_backup.json': {'content': '{"workspaces": []}'}
        }
    })
    with patch('urllib.request.urlopen', return_value=mock_resp):
        content = fetch_gist('token', 'gist123')
    assert content == '{"workspaces": []}'


def test_list_user_gists_filters_by_filename():
    from app.gist_sync import list_user_gists
    mock_data = [
        {'id': 'g1', 'files': {'Orbit_backup.json': {'filename': 'Orbit_backup.json'}}},
        {'id': 'g2', 'files': {'other_file.txt': {}}},
        {'id': 'g3', 'files': {'Orbit_backup.json': {}, 'extra.md': {}}},
    ]
    mock_resp = _make_response(mock_data)
    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = list_user_gists('token')
    assert len(result) == 2
    assert {g['id'] for g in result} == {'g1', 'g3'}


def test_list_user_gists_empty():
    from app.gist_sync import list_user_gists
    mock_resp = _make_response([])
    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = list_user_gists('token')
    assert result == []


def test_create_gist_network_error_raises():
    from app.gist_sync import create_gist
    with patch('urllib.request.urlopen', side_effect=Exception('Connection refused')):
        with pytest.raises(Exception):
            create_gist('token', 'content')


def test_fetch_gist_network_error_raises():
    from app.gist_sync import fetch_gist
    with patch('urllib.request.urlopen', side_effect=Exception('Timeout')):
        with pytest.raises(Exception):
            fetch_gist('token', 'gist_id')


def test_update_gist_network_error_raises():
    from app.gist_sync import update_gist
    with patch('urllib.request.urlopen', side_effect=Exception('Network down')):
        with pytest.raises(Exception):
            update_gist('token', 'gid', 'content')


def test_headers_structure():
    from app.gist_sync import _headers
    h = _headers('test_token')
    assert 'Authorization' in h
    assert 'Accept' in h
    assert 'Content-Type' in h
    assert 'User-Agent' in h
    assert 'test_token' in h['Authorization']

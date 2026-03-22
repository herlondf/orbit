"""Extended tests for app.updater — MSI/ZIP asset selection, changelog, download, install."""
import json
import os
import pytest
from unittest.mock import MagicMock, patch


def _mock_response(data: dict):
    body = json.dumps(data).encode()
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read = MagicMock(return_value=body)
    mock_resp.headers = {'Content-Length': str(len(body))}
    return mock_resp


# ── MSI/ZIP asset selection (lines 45-54) ─────────────────────────────────────

def test_check_update_picks_msi_asset():
    from app.updater import check_for_update
    assets = [
        {'name': 'Orbit-99.0.0-win-x64.msi', 'browser_download_url': 'https://dl/orbit.msi'},
        {'name': 'Orbit-99.0.0-win-x64.zip', 'browser_download_url': 'https://dl/orbit.zip'},
    ]
    mock_resp = _mock_response({'tag_name': 'v99.0.0', 'html_url': 'https://github.com/r', 'assets': assets})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is True
    assert dl_url == 'https://dl/orbit.msi'


def test_check_update_falls_back_to_zip_when_no_msi():
    from app.updater import check_for_update
    assets = [
        {'name': 'Orbit-99.0.0-win-x64.zip', 'browser_download_url': 'https://dl/orbit.zip'},
    ]
    mock_resp = _mock_response({'tag_name': 'v99.0.0', 'html_url': 'https://github.com/r', 'assets': assets})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is True
    assert dl_url == 'https://dl/orbit.zip'


def test_check_update_skips_non_win64_msi():
    from app.updater import check_for_update
    assets = [
        {'name': 'Orbit-99.0.0-linux.msi', 'browser_download_url': 'https://dl/linux.msi'},
        {'name': 'Orbit-99.0.0-win-x64.zip', 'browser_download_url': 'https://dl/orbit.zip'},
    ]
    mock_resp = _mock_response({'tag_name': 'v99.0.0', 'html_url': 'https://github.com/r', 'assets': assets})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    # Should skip linux.msi and use zip
    assert dl_url == 'https://dl/orbit.zip'


def test_check_update_no_assets():
    from app.updater import check_for_update
    mock_resp = _mock_response({'tag_name': 'v99.0.0', 'html_url': 'https://github.com/r', 'assets': []})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        has_update, version, url, dl_url = check_for_update()
    assert has_update is True
    assert dl_url == ''


# ── get_changelog (lines 66-73) ───────────────────────────────────────────────

def test_get_changelog_success():
    from app.updater import get_changelog
    body = '## What changed\n- New feature\n- Bug fix'
    mock_resp = _mock_response({'body': body})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = get_changelog('1.2.3')
    assert result == body


def test_get_changelog_empty_body():
    from app.updater import get_changelog
    mock_resp = _mock_response({})
    with patch('urllib.request.urlopen', return_value=mock_resp):
        result = get_changelog('1.0.0')
    assert result == ''


def test_get_changelog_network_error():
    from app.updater import get_changelog
    with patch('urllib.request.urlopen', side_effect=Exception('Network error')):
        result = get_changelog('1.0.0')
    assert result == ''


# ── download_update (lines 85-104) ────────────────────────────────────────────

def test_download_update_msi(tmp_path):
    from app.updater import download_update
    fake_content = b'MSI_DATA' * 100
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {'Content-Length': str(len(fake_content))}
    mock_resp.read = MagicMock(side_effect=[fake_content, b''])

    with patch('urllib.request.urlopen', return_value=mock_resp), \
         patch('tempfile.mkstemp', return_value=(0, str(tmp_path / 'orbit-update-.msi'))), \
         patch('os.close'):
        path = download_update('https://example.com/Orbit.msi')
    assert path.endswith('.msi')


def test_download_update_zip(tmp_path):
    from app.updater import download_update
    fake_content = b'ZIP_DATA' * 50
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {'Content-Length': str(len(fake_content))}
    mock_resp.read = MagicMock(side_effect=[fake_content, b''])

    with patch('urllib.request.urlopen', return_value=mock_resp), \
         patch('tempfile.mkstemp', return_value=(0, str(tmp_path / 'orbit-update-.zip'))), \
         patch('os.close'):
        path = download_update('https://example.com/Orbit.zip')
    assert path.endswith('.zip')


def test_download_update_calls_progress_cb(tmp_path):
    from app.updater import download_update
    fake_content = b'DATA' * 100
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {'Content-Length': str(len(fake_content))}
    mock_resp.read = MagicMock(side_effect=[fake_content, b''])

    progress_calls = []
    def progress_cb(downloaded, total):
        progress_calls.append((downloaded, total))

    with patch('urllib.request.urlopen', return_value=mock_resp), \
         patch('tempfile.mkstemp', return_value=(0, str(tmp_path / 'orbit-update-.msi'))), \
         patch('os.close'):
        download_update('https://example.com/Orbit.msi', progress_cb=progress_cb)
    assert len(progress_calls) > 0


# ── install_update (lines 113-124) ────────────────────────────────────────────

def test_install_update_msi():
    from app.updater import install_update
    with patch('subprocess.Popen') as mock_popen, \
         patch('PySide6.QtWidgets.QApplication.quit') as mock_quit:
        install_update('C:\\path\\to\\orbit.msi')
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert 'msiexec' in args
    assert 'C:\\path\\to\\orbit.msi' in args
    mock_quit.assert_called_once()


def test_install_update_zip(tmp_path):
    from app.updater import install_update
    zip_path = str(tmp_path / 'orbit.zip')
    with patch('os.startfile', create=True) as mock_startfile, \
         patch('PySide6.QtWidgets.QApplication.quit') as mock_quit:
        install_update(zip_path)
    mock_startfile.assert_called_once_with(str(tmp_path))
    mock_quit.assert_called_once()


# ── _version_gt edge cases (line 131-132) ────────────────────────────────────

def test_version_gt_malformed():
    from app.updater import _version_gt
    # Malformed version strings should not raise
    assert _version_gt('abc', '1.0.0') is False
    assert _version_gt('1.0.0', 'xyz') is True

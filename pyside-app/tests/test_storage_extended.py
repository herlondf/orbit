"""Extended tests for app.storage — covering error paths."""
import json
import os
import pytest


def test_save_services_creates_file(tmp_appdata, sample_service):
    from app.storage import save_services, STORAGE_FILE
    import app.storage as s
    save_services([sample_service])
    assert os.path.exists(s.STORAGE_FILE)


def test_load_services_empty_file_returns_empty_list(tmp_appdata):
    from app.storage import load_services
    result = load_services()
    assert result == []


def test_load_services_corrupt_file_returns_empty(tmp_appdata):
    import app.storage as s
    # Write corrupt JSON to storage file
    with open(s.STORAGE_FILE, 'w') as f:
        f.write('NOT VALID JSON }{')
    result = s.load_services()
    assert result == []


def test_load_services_valid_file(tmp_appdata, sample_service):
    from app.storage import save_services, load_services
    save_services([sample_service])
    result = load_services()
    assert len(result) == 1
    assert result[0].id == 'svc1'


def test_load_settings_corrupt_file_returns_empty(tmp_appdata):
    import app.storage as s
    with open(s._SETTINGS_FILE, 'w') as f:
        f.write('INVALID {{{')
    result = s.load_settings()
    assert result == {}


def test_load_workspaces_corrupt_file_falls_back_to_default(tmp_appdata):
    import app.storage as s
    # Write corrupt JSON to workspaces file
    with open(s._WORKSPACES_FILE, 'w') as f:
        f.write('CORRUPT JSON')
    result = s.load_workspaces()
    # Should fallback to default workspace from old services
    assert len(result) >= 1
    assert result[0].id == 'ws-default'


def test_load_workspaces_empty_list_in_file_falls_back(tmp_appdata):
    import app.storage as s
    from app.encryption import write_json_file, get_session_password
    # Write empty list - should fall back to default
    write_json_file(s._WORKSPACES_FILE, [], password=get_session_password())
    result = s.load_workspaces()
    assert result[0].id == 'ws-default'


def test_save_and_load_services_roundtrip(tmp_appdata, sample_service):
    from app.storage import save_services, load_services
    save_services([sample_service])
    result = load_services()
    assert len(result) == 1
    assert result[0].name == 'Slack Test'
    assert len(result[0].accounts) == 1
    assert result[0].accounts[0].id == 'acc1'

"""Extended tests for app.importer — covering edge cases."""
import json
import pytest
from pathlib import Path


def _write_json(path, data):
    Path(path).write_text(json.dumps(data), encoding='utf-8')


def test_import_rambox_workspaces_key(tmp_path):
    """Test the 'workspaces' key path in import_rambox (line 62-63)."""
    from app.importer import import_rambox
    data = {
        'workspaces': [
            {
                'services': [
                    {'name': 'Slack', 'type': 'Slack', 'url': 'https://app.slack.com'},
                ]
            }
        ]
    }
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws is not None
    assert len(ws.services) == 1
    assert ws.services[0].name == 'Slack'


def test_import_ferdium_non_dict_recipe(tmp_path):
    """Test ferdium import when recipe is not a dict (line 108)."""
    from app.importer import import_ferdium
    data = {
        'services': [
            {
                'name': 'Custom Service',
                'recipe': 'slack',  # string, not dict
                'type': 'slack',
                'url': 'https://app.slack.com',
            }
        ]
    }
    f = tmp_path / 'ferdium.json'
    _write_json(f, data)
    ws = import_ferdium(str(f))
    assert ws is not None
    assert len(ws.services) == 1
    # When recipe is not a dict, falls back to svc_data.get('type', '')
    assert ws.services[0].service_type == 'slack'


def test_import_ferdium_non_dict_recipe_unknown(tmp_path):
    """Non-dict recipe with unknown type maps to custom."""
    from app.importer import import_ferdium
    data = {
        'services': [
            {
                'name': 'Unknown',
                'recipe': 'unknown_recipe_string',
                'type': 'unknown_type',
                'url': '',
            }
        ]
    }
    f = tmp_path / 'ferdium.json'
    _write_json(f, data)
    ws = import_ferdium(str(f))
    assert ws.services[0].service_type == 'custom'


def test_import_rambox_workspaces_key_empty_services(tmp_path):
    """workspaces key with empty services list."""
    from app.importer import import_rambox
    data = {'workspaces': [{'services': []}]}
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws is not None
    assert len(ws.services) == 0

"""Tests for app.importer — Rambox/Ferdium import logic."""
import json
import pytest
from pathlib import Path


def _write_json(path, data):
    Path(path).write_text(json.dumps(data), encoding='utf-8')


def test_service_map_has_min_entries():
    from app.importer import SERVICE_MAP
    assert len(SERVICE_MAP) >= 10


def test_service_map_covers_common_services():
    from app.importer import SERVICE_MAP
    for name in ('WhatsApp', 'Slack', 'Gmail', 'Telegram', 'Discord'):
        assert name in SERVICE_MAP


def test_import_rambox_list_format(tmp_path):
    from app.importer import import_rambox
    data = [
        {'name': 'My Slack', 'type': 'Slack', 'url': 'https://app.slack.com'},
        {'name': 'My WhatsApp', 'type': 'WhatsApp', 'url': 'https://web.whatsapp.com'},
    ]
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws is not None
    assert len(ws.services) == 2
    names = [s.name for s in ws.services]
    assert 'My Slack' in names
    assert 'My WhatsApp' in names


def test_import_rambox_dict_with_services_key(tmp_path):
    from app.importer import import_rambox
    data = {
        'services': [
            {'name': 'Work Slack', 'type': 'Slack', 'url': 'https://app.slack.com'},
        ]
    }
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws is not None
    assert len(ws.services) == 1
    assert ws.services[0].name == 'Work Slack'


def test_import_rambox_unknown_type_maps_to_custom(tmp_path):
    from app.importer import import_rambox
    data = [{'name': 'Exotic App', 'type': 'SomethingUnknown', 'url': 'https://example.com'}]
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws.services[0].service_type == 'custom'


def test_import_rambox_service_has_account(tmp_path):
    from app.importer import import_rambox
    data = [{'name': 'Telegram', 'type': 'Telegram', 'url': 'https://web.telegram.org'}]
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    svc = ws.services[0]
    assert len(svc.accounts) == 1
    assert svc.accounts[0].url == 'https://web.telegram.org'


def test_import_rambox_empty_services(tmp_path):
    from app.importer import import_rambox
    data = []
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws is not None
    assert len(ws.services) == 0


def test_import_rambox_invalid_json_raises(tmp_path):
    from app.importer import import_rambox
    f = tmp_path / 'bad.json'
    f.write_text('NOT JSON', encoding='utf-8')
    with pytest.raises(ValueError):
        import_rambox(str(f))


def test_import_rambox_workspace_name(tmp_path):
    from app.importer import import_rambox
    data = [{'name': 'Slack', 'type': 'Slack', 'url': ''}]
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws.name == 'Importado'


def test_import_ferdium_services_key(tmp_path):
    from app.importer import import_ferdium
    data = {
        'services': [
            {'name': 'Discord', 'type': 'discord', 'url': 'https://discord.com/app'},
        ]
    }
    f = tmp_path / 'ferdium.json'
    _write_json(f, data)
    ws = import_ferdium(str(f))
    assert ws is not None
    assert len(ws.services) == 1
    assert ws.services[0].name == 'Discord'


def test_import_ferdium_with_recipe(tmp_path):
    from app.importer import import_ferdium
    data = {
        'services': [
            {'name': 'Slack', 'recipe': {'id': 'slack'}, 'url': ''},
        ]
    }
    f = tmp_path / 'ferdium.json'
    _write_json(f, data)
    ws = import_ferdium(str(f))
    assert ws.services[0].service_type == 'slack'


def test_import_ferdium_workspace_name(tmp_path):
    from app.importer import import_ferdium
    data = {'services': []}
    f = tmp_path / 'ferdium.json'
    _write_json(f, data)
    ws = import_ferdium(str(f))
    assert ws.name == 'Ferdium Import'


def test_import_ferdium_invalid_json_raises(tmp_path):
    from app.importer import import_ferdium
    f = tmp_path / 'bad.json'
    f.write_text('INVALID', encoding='utf-8')
    with pytest.raises(ValueError):
        import_ferdium(str(f))


def test_import_rambox_service_type_mapped(tmp_path):
    from app.importer import import_rambox
    data = [{'name': 'Teams', 'type': 'Microsoft Teams', 'url': ''}]
    f = tmp_path / 'rambox.json'
    _write_json(f, data)
    ws = import_rambox(str(f))
    assert ws.services[0].service_type == 'teams'


def test_import_ferdium_unknown_type_maps_custom(tmp_path):
    from app.importer import import_ferdium
    data = {'services': [{'name': 'Unknown', 'type': 'totally_unknown', 'url': ''}]}
    f = tmp_path / 'ferdium.json'
    _write_json(f, data)
    ws = import_ferdium(str(f))
    assert ws.services[0].service_type == 'custom'

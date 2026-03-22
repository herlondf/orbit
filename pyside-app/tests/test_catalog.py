"""Tests for app.catalog — catalog entries and google_url helper."""
import pytest


def test_catalog_has_minimum_entries():
    from app.catalog import CATALOG
    assert len(CATALOG) >= 20


def test_catalog_entry_required_fields():
    from app.catalog import CATALOG
    for entry in CATALOG:
        assert entry.type, f"Entry missing type: {entry}"
        assert entry.name, f"Entry missing name: {entry}"
        assert entry.icon, f"Entry missing icon: {entry}"
        assert entry.color, f"Entry missing color: {entry}"
        assert entry.default_url is not None, f"Entry missing default_url: {entry}"
        assert entry.description is not None


def test_catalog_ids_unique():
    from app.catalog import CATALOG
    ids = [e.type for e in CATALOG]
    assert len(ids) == len(set(ids)), "Duplicate service type IDs in CATALOG"


def test_catalog_has_favicon_url():
    from app.catalog import CATALOG
    # Most entries should have a favicon_url (custom may not)
    entries_with_favicon = [e for e in CATALOG if e.favicon_url]
    assert len(entries_with_favicon) >= 15


def test_google_url_gmail():
    from app.catalog import google_url
    url = google_url('gmail', 0)
    assert url == 'https://mail.google.com/mail/u/0/'


def test_google_url_authuser_index():
    from app.catalog import google_url
    url = google_url('gchat', 2)
    assert 'u/2' in url


def test_google_url_gmeet():
    from app.catalog import google_url
    url = google_url('gmeet', 1)
    assert 'authuser=1' in url


def test_google_url_gcalendar():
    from app.catalog import google_url
    url = google_url('gcalendar', 0)
    assert 'u/0' in url


def test_google_url_unknown_type():
    from app.catalog import google_url
    url = google_url('slack', 0)
    assert url == ''


def test_google_types_subset_of_catalog():
    from app.catalog import GOOGLE_TYPES, CATALOG
    catalog_ids = {e.type for e in CATALOG}
    for gtype in GOOGLE_TYPES:
        assert gtype in catalog_ids, f"GOOGLE_TYPE '{gtype}' not in CATALOG"


def test_google_types_has_expected_services():
    from app.catalog import GOOGLE_TYPES
    assert 'gmail' in GOOGLE_TYPES
    assert 'gchat' in GOOGLE_TYPES
    assert 'gcalendar' in GOOGLE_TYPES
    assert 'gmeet' in GOOGLE_TYPES


def test_get_entry_found():
    from app.catalog import get_entry
    entry = get_entry('slack')
    assert entry is not None
    assert entry.name == 'Slack'


def test_get_entry_not_found():
    from app.catalog import get_entry
    entry = get_entry('nonexistent_service')
    assert entry is None


def test_catalog_color_is_hex():
    from app.catalog import CATALOG
    for entry in CATALOG:
        if entry.color:
            assert entry.color.startswith('#'), f"{entry.type} color not hex: {entry.color}"


def test_catalog_has_common_services():
    from app.catalog import CATALOG
    types = {e.type for e in CATALOG}
    for expected in ('slack', 'whatsapp', 'telegram', 'discord', 'gmail', 'notion', 'github'):
        assert expected in types, f"Expected service '{expected}' not in CATALOG"

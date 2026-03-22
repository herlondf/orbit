"""Extended tests for app.catalog — covering get_all_categories()."""
import pytest


def test_get_all_categories_returns_list():
    from app.catalog import get_all_categories
    cats = get_all_categories()
    assert isinstance(cats, list)


def test_get_all_categories_not_empty():
    from app.catalog import get_all_categories
    cats = get_all_categories()
    assert len(cats) > 0


def test_get_all_categories_sorted():
    from app.catalog import get_all_categories
    cats = get_all_categories()
    assert cats == sorted(cats)


def test_get_all_categories_unique():
    from app.catalog import get_all_categories
    cats = get_all_categories()
    assert len(cats) == len(set(cats))


def test_get_all_categories_includes_expected():
    from app.catalog import get_all_categories
    cats = get_all_categories()
    for expected in ('Trabalho', 'Mensagens', 'Dev', 'Google'):
        assert expected in cats, f"Expected category '{expected}' not found"


def test_get_all_categories_no_empty_strings():
    from app.catalog import get_all_categories
    cats = get_all_categories()
    for cat in cats:
        assert cat, "Empty category string found"


def test_catalog_has_categories_field():
    from app.catalog import CATALOG
    cats_in_catalog = {e.category for e in CATALOG if e.category}
    assert len(cats_in_catalog) > 0


def test_get_entry_returns_none_for_unknown():
    from app.catalog import get_entry
    assert get_entry('totally_unknown_xyz') is None


def test_get_entry_whatsapp():
    from app.catalog import get_entry
    entry = get_entry('whatsapp')
    assert entry is not None
    assert entry.type == 'whatsapp'
    assert entry.category == 'Mensagens'

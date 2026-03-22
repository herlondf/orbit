"""Tests for app.reading_list — reading list storage."""
import json
import os
import pytest


@pytest.fixture(autouse=True)
def patch_reading_list_path(tmp_path, monkeypatch):
    """Redirect reading_list _path() to use tmp dir."""
    import app.reading_list as rl
    orbit_dir = tmp_path / 'Orbit'
    orbit_dir.mkdir(parents=True, exist_ok=True)
    rl_path = str(orbit_dir / 'reading_list.json')
    monkeypatch.setenv('APPDATA', str(tmp_path))
    return rl_path


def test_add_to_reading_list(tmp_appdata):
    import app.reading_list as rl
    result = rl.add_to_reading_list('https://example.com', 'Example', 'Browser')
    assert result is True
    items = rl.load_reading_list()
    assert len(items) == 1
    assert items[0].url == 'https://example.com'


def test_add_duplicate_returns_false(tmp_appdata):
    import app.reading_list as rl
    rl.add_to_reading_list('https://example.com', 'Example', 'Browser')
    result = rl.add_to_reading_list('https://example.com', 'Example', 'Browser')
    assert result is False
    items = rl.load_reading_list()
    assert len(items) == 1


def test_mark_read(tmp_appdata):
    import app.reading_list as rl
    rl.add_to_reading_list('https://example.com', 'Example', 'Browser')
    rl.mark_read('https://example.com')
    items = rl.load_reading_list()
    assert items[0].read is True


def test_remove_item(tmp_appdata):
    import app.reading_list as rl
    rl.add_to_reading_list('https://a.com', 'A', 'Browser')
    rl.add_to_reading_list('https://b.com', 'B', 'Browser')
    rl.remove_item('https://a.com')
    items = rl.load_reading_list()
    urls = [i.url for i in items]
    assert 'https://a.com' not in urls
    assert 'https://b.com' in urls


def test_load_reading_list_missing_file(tmp_appdata):
    import app.reading_list as rl
    items = rl.load_reading_list()
    assert items == []


def test_add_uses_url_as_title_when_empty(tmp_appdata):
    import app.reading_list as rl
    rl.add_to_reading_list('https://example.com', '', 'Browser')
    items = rl.load_reading_list()
    assert items[0].title == 'https://example.com'

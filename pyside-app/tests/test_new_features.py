"""Tests for app.workspace_schedule and app.reading_list."""
import pytest
from unittest.mock import patch


# ── workspace_schedule ────────────────────────────────────────────────────────

def test_load_schedule_empty(tmp_appdata):
    from app.workspace_schedule import load_schedule
    config = load_schedule()
    assert config.enabled is False
    assert config.rules == []


def test_save_and_load_schedule(tmp_appdata):
    from app.workspace_schedule import WorkspaceRule, ScheduleConfig, save_schedule, load_schedule
    rule = WorkspaceRule(workspace_id='ws-1', days=[0, 1, 2], start_hour=9, end_hour=18)
    config = ScheduleConfig(rules=[rule], enabled=True)
    save_schedule(config)
    loaded = load_schedule()
    assert loaded.enabled is True
    assert len(loaded.rules) == 1
    assert loaded.rules[0].workspace_id == 'ws-1'
    assert loaded.rules[0].days == [0, 1, 2]
    assert loaded.rules[0].start_hour == 9
    assert loaded.rules[0].end_hour == 18


def test_get_active_workspace_id_disabled():
    from app.workspace_schedule import WorkspaceRule, ScheduleConfig, get_active_workspace_id

    class FakeWS:
        id = 'ws-1'

    rule = WorkspaceRule(workspace_id='ws-1', days=list(range(7)), start_hour=0, end_hour=23)
    config = ScheduleConfig(rules=[rule], enabled=False)
    result = get_active_workspace_id(config, [FakeWS()])
    assert result is None


def test_get_active_workspace_id_matches():
    from app.workspace_schedule import WorkspaceRule, ScheduleConfig, get_active_workspace_id
    from datetime import datetime

    class FakeWS:
        id = 'ws-1'

    now = datetime.now()
    rule = WorkspaceRule(
        workspace_id='ws-1',
        days=list(range(7)),
        start_hour=0,
        end_hour=23,
        start_minute=0,
        end_minute=59,
    )
    config = ScheduleConfig(rules=[rule], enabled=True)
    result = get_active_workspace_id(config, [FakeWS()])
    assert result == 'ws-1'


def test_get_active_workspace_id_nonexistent_workspace():
    from app.workspace_schedule import WorkspaceRule, ScheduleConfig, get_active_workspace_id

    class FakeWS:
        id = 'ws-other'

    rule = WorkspaceRule(workspace_id='ws-missing', days=list(range(7)), start_hour=0, end_hour=23)
    config = ScheduleConfig(rules=[rule], enabled=True)
    result = get_active_workspace_id(config, [FakeWS()])
    assert result is None


def test_get_active_workspace_id_rule_disabled():
    from app.workspace_schedule import WorkspaceRule, ScheduleConfig, get_active_workspace_id

    class FakeWS:
        id = 'ws-1'

    rule = WorkspaceRule(workspace_id='ws-1', days=list(range(7)), start_hour=0, end_hour=23, enabled=False)
    config = ScheduleConfig(rules=[rule], enabled=True)
    result = get_active_workspace_id(config, [FakeWS()])
    assert result is None


# ── reading_list ──────────────────────────────────────────────────────────────

def test_load_reading_list_empty(tmp_appdata):
    from app.reading_list import load_reading_list
    items = load_reading_list()
    assert items == []


def test_add_to_reading_list(tmp_appdata):
    from app.reading_list import add_to_reading_list, load_reading_list
    added = add_to_reading_list('https://example.com', 'Example', 'TestSvc')
    assert added is True
    items = load_reading_list()
    assert len(items) == 1
    assert items[0].url == 'https://example.com'
    assert items[0].title == 'Example'
    assert items[0].service_name == 'TestSvc'
    assert items[0].read is False


def test_add_duplicate_reading_list(tmp_appdata):
    from app.reading_list import add_to_reading_list
    add_to_reading_list('https://example.com', 'Example', 'TestSvc')
    added = add_to_reading_list('https://example.com', 'Example2', 'TestSvc')
    assert added is False


def test_mark_read(tmp_appdata):
    from app.reading_list import add_to_reading_list, mark_read, load_reading_list
    add_to_reading_list('https://example.com', 'Example', 'TestSvc')
    mark_read('https://example.com')
    items = load_reading_list()
    assert items[0].read is True


def test_remove_item(tmp_appdata):
    from app.reading_list import add_to_reading_list, remove_item, load_reading_list
    add_to_reading_list('https://example.com', 'Example', 'TestSvc')
    add_to_reading_list('https://other.com', 'Other', 'TestSvc')
    remove_item('https://example.com')
    items = load_reading_list()
    assert len(items) == 1
    assert items[0].url == 'https://other.com'


def test_reading_list_max_200(tmp_appdata):
    from app.reading_list import add_to_reading_list, load_reading_list
    for i in range(205):
        add_to_reading_list(f'https://example.com/{i}', f'Title {i}', 'Svc')
    items = load_reading_list()
    assert len(items) <= 200

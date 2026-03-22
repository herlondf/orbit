"""Tests for app.stats — session recording, weekly totals, duration formatting."""
import json
import pytest
from datetime import date, timedelta
from unittest.mock import patch


def test_fmt_duration_zero():
    from app.stats import fmt_duration
    assert fmt_duration(0) == '0s'


def test_fmt_duration_seconds():
    from app.stats import fmt_duration
    assert fmt_duration(59) == '59s'
    assert fmt_duration(1) == '1s'


def test_fmt_duration_minutes():
    from app.stats import fmt_duration
    result = fmt_duration(60)
    assert 'min' in result
    result2 = fmt_duration(90)
    assert 'min' in result2


def test_fmt_duration_hours():
    from app.stats import fmt_duration
    result = fmt_duration(3661)
    assert 'h' in result
    assert 'min' in result


def test_fmt_duration_exactly_one_hour():
    from app.stats import fmt_duration
    result = fmt_duration(3600)
    assert 'h' in result


def test_record_session_saves(tmp_appdata):
    from app.stats import record_session, load_stats
    record_session('svc1', 'Slack', 120)
    data = load_stats()
    assert 'svc1' in data
    assert data['svc1']['name'] == 'Slack'
    today = date.today().strftime('%Y-%m-%d')
    assert data['svc1']['days'][today] == 120


def test_record_session_accumulates(tmp_appdata):
    from app.stats import record_session, load_stats
    record_session('svc1', 'Slack', 100)
    record_session('svc1', 'Slack', 200)
    data = load_stats()
    today = date.today().strftime('%Y-%m-%d')
    assert data['svc1']['days'][today] == 300


def test_record_session_multiple_services(tmp_appdata):
    from app.stats import record_session, load_stats
    record_session('svc1', 'Slack', 60)
    record_session('svc2', 'Gmail', 90)
    data = load_stats()
    assert 'svc1' in data
    assert 'svc2' in data


def test_record_session_ignores_sub_second(tmp_appdata):
    from app.stats import record_session, load_stats
    record_session('svc1', 'Slack', 0.5)
    data = load_stats()
    assert 'svc1' not in data


def test_get_weekly_totals_sorted(tmp_appdata):
    from app.stats import record_session, get_weekly_totals
    record_session('svc1', 'Slack', 300)
    record_session('svc2', 'Gmail', 600)
    totals = get_weekly_totals()
    assert len(totals) == 2
    assert totals[0]['name'] == 'Gmail'
    assert totals[1]['name'] == 'Slack'


def test_get_weekly_totals_structure(tmp_appdata):
    from app.stats import record_session, get_weekly_totals
    record_session('svc1', 'Slack', 60)
    totals = get_weekly_totals()
    assert len(totals) == 1
    entry = totals[0]
    assert 'id' in entry
    assert 'name' in entry
    assert 'total' in entry
    assert entry['total'] == 60


def test_get_weekly_totals_excludes_old_entries(tmp_appdata):
    """Entries older than 7 days should not appear in weekly totals."""
    import app.stats as stats_mod
    old_date = (date.today() - timedelta(days=8)).strftime('%Y-%m-%d')
    data = {'svc_old': {'name': 'OldService', 'days': {old_date: 9999}}}
    with open(stats_mod._STATS_FILE, 'w') as f:
        json.dump(data, f)
    totals = stats_mod.get_weekly_totals()
    assert all(t['id'] != 'svc_old' for t in totals)


def test_get_weekly_totals_empty(tmp_appdata):
    from app.stats import get_weekly_totals
    totals = get_weekly_totals()
    assert totals == []


def test_load_stats_missing_file(tmp_appdata):
    from app.stats import load_stats
    data = load_stats()
    assert data == {}


def test_record_session_updates_name(tmp_appdata):
    from app.stats import record_session, load_stats
    record_session('svc1', 'Old Name', 60)
    record_session('svc1', 'New Name', 60)
    data = load_stats()
    assert data['svc1']['name'] == 'New Name'

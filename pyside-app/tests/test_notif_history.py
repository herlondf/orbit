"""Tests for app.notif_history — notification history storage."""
import pytest


def test_add_notification(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'New message', 'You have mail')
    hist = nh.get_history()
    assert len(hist) == 1
    entry = hist[0]
    assert entry.service_id == 'svc1'
    assert entry.service_name == 'Slack'
    assert entry.title == 'New message'
    assert entry.body == 'You have mail'
    assert entry.timestamp  # non-empty ISO string


def test_add_notification_no_body(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'Ping')
    hist = nh.get_history()
    assert hist[0].body == ''


def test_get_history_returns_copy(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'A')
    hist = nh.get_history()
    hist.append('garbage')
    assert len(nh.get_history()) == 1


def test_history_newest_first(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'First')
    nh.add_notification('svc2', 'Gmail', 'Second')
    hist = nh.get_history()
    assert hist[0].title == 'Second'
    assert hist[1].title == 'First'


def test_history_capped_at_50(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    for i in range(55):
        nh.add_notification('svc1', 'Slack', f'Msg {i}')
    hist = nh.get_history()
    assert len(hist) == 50


def test_clear_history(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'X')
    nh.clear_history()
    assert nh.get_history() == []


def test_clear_history_persists(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'X')
    nh.clear_history()
    nh.load_history()
    assert nh.get_history() == []


def test_load_history_restores(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'Restored msg')
    # Clear in-memory and reload from disk
    nh._history.clear()
    nh.load_history()
    hist = nh.get_history()
    assert len(hist) == 1
    assert hist[0].title == 'Restored msg'


def test_notif_entry_fields():
    from app.notif_history import NotifEntry
    entry = NotifEntry(
        service_id='s1', service_name='Slack', title='Hi',
        body='There', timestamp='2024-01-01T10:00:00'
    )
    assert entry.service_id == 's1'
    assert entry.service_name == 'Slack'
    assert entry.title == 'Hi'
    assert entry.body == 'There'
    assert entry.timestamp == '2024-01-01T10:00:00'


def test_load_history_missing_file(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.load_history()
    assert nh.get_history() == []


def test_multiple_services_in_history(tmp_appdata):
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'Msg A')
    nh.add_notification('svc2', 'Gmail', 'Msg B')
    nh.add_notification('svc3', 'Teams', 'Msg C')
    hist = nh.get_history()
    service_ids = {e.service_id for e in hist}
    assert service_ids == {'svc1', 'svc2', 'svc3'}

"""Extended tests for app.notif_history — covering exception paths."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_history_corrupt_file_clears_history(tmp_appdata):
    """load_history() with corrupt JSON should set _history to [] (lines 50-51)."""
    import app.notif_history as nh
    nh._history.clear()
    nh.HISTORY_FILE.write_text('NOT VALID JSON }{', encoding='utf-8')
    nh.load_history()
    assert nh.get_history() == []


def test_save_error_is_handled_gracefully(tmp_appdata, capsys):
    """_save() should handle write errors gracefully (lines 61-62)."""
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Test', 'Hello')

    # Make write_text raise an exception
    with patch.object(Path, 'write_text', side_effect=PermissionError('access denied')):
        # Should not raise
        nh._save()


def test_load_history_from_valid_file(tmp_appdata):
    """load_history() correctly reads valid JSON."""
    import app.notif_history as nh
    nh._history.clear()
    nh.add_notification('svc1', 'Slack', 'Test')
    nh._history.clear()
    nh.load_history()
    hist = nh.get_history()
    assert len(hist) == 1
    assert hist[0].title == 'Test'


def test_history_max_50_items_after_add(tmp_appdata):
    """Verify history stays at max 50 and pop works (covers line 29-30)."""
    import app.notif_history as nh
    nh._history.clear()
    for i in range(52):
        nh.add_notification('svc1', 'Test', f'Msg {i}')
    assert len(nh.get_history()) == 50

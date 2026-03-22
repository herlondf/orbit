"""Tests for app.quiet_hours — DND schedule logic."""
import pytest
from unittest.mock import patch
from datetime import datetime


def _settings(enabled=True, start='22:00', end='08:00', days=None):
    if days is None:
        days = list(range(7))  # all days
    return {
        'quiet_hours': {
            'enabled': enabled,
            'start': start,
            'end': end,
            'days': days,
        }
    }


def test_no_quiet_hours_config():
    from app.quiet_hours import is_quiet_now
    assert is_quiet_now({}) is False


def test_quiet_hours_disabled():
    from app.quiet_hours import is_quiet_now
    settings = _settings(enabled=False)
    assert is_quiet_now(settings) is False


def test_quiet_hours_empty_config_key():
    from app.quiet_hours import is_quiet_now
    assert is_quiet_now({'quiet_hours': {}}) is False


def test_in_range_daytime(monkeypatch):
    """Time is inside a daytime range (09:00–17:00)."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 12, 0)  # Monday noon
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='09:00', end='17:00', days=[0, 1, 2, 3, 4])
        assert is_quiet_now(settings) is True


def test_outside_range_daytime(monkeypatch):
    """Time is outside a daytime range (09:00–17:00)."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 18, 30)  # Monday 18:30
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='09:00', end='17:00', days=[0, 1, 2, 3, 4])
        assert is_quiet_now(settings) is False


def test_overnight_range_inside(monkeypatch):
    """23:00 is inside overnight range 22:00–08:00."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 23, 0)  # Monday 23:00
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='22:00', end='08:00', days=[0])
        assert is_quiet_now(settings) is True


def test_overnight_range_early_morning_inside(monkeypatch):
    """02:00 is inside overnight range 22:00–08:00."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 2, 0)  # Monday 02:00
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='22:00', end='08:00', days=[0])
        assert is_quiet_now(settings) is True


def test_overnight_range_outside(monkeypatch):
    """09:00 is outside overnight range 22:00–08:00."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 9, 0)  # Monday 09:00
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='22:00', end='08:00', days=[0])
        assert is_quiet_now(settings) is False


def test_day_filter_wrong_day(monkeypatch):
    """Today (Monday=0) not in configured days → False."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 23, 0)  # Monday
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='22:00', end='08:00', days=[1, 2, 3])  # Tue-Thu
        assert is_quiet_now(settings) is False


def test_day_filter_correct_day(monkeypatch):
    """Today (Monday=0) IS in configured days → True."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 23, 0)  # Monday
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='22:00', end='08:00', days=[0, 1])
        assert is_quiet_now(settings) is True


def test_exact_start_boundary(monkeypatch):
    """Exact start time (22:00) should be considered quiet."""
    from app.quiet_hours import is_quiet_now
    fake_now = datetime(2024, 1, 15, 22, 0)  # Monday 22:00
    with patch('app.quiet_hours.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        settings = _settings(enabled=True, start='22:00', end='23:59', days=[0])
        assert is_quiet_now(settings) is True

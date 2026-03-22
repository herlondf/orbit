"""
audit_log.py — Lightweight audit trail for Orbit.

Records security-relevant and user-action events to a JSON-lines file.
Only the last 500 events are retained.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List

_MAX_EVENTS = 500

_APPDATA = os.environ.get('APPDATA', os.path.expanduser('~'))
_DEFAULT_LOG_PATH = os.path.join(_APPDATA, 'Orbit', 'audit.log')

# Allow override at module level (used by portable mode)
_log_path: str = _DEFAULT_LOG_PATH


def set_log_path(path: str) -> None:
    """Override the default log file path (call before any log_event calls)."""
    global _log_path
    _log_path = path


def get_log_path() -> str:
    """Return the current log file path."""
    return _log_path


def log_event(event_type: str, detail: str = '') -> None:
    """
    Append a structured event entry to the audit log.

    Parameters
    ----------
    event_type:
        One of: app_start, app_exit, locked, unlocked, workspace_switched,
        service_added, service_removed, config_changed, encryption_enabled,
        encryption_disabled.
    detail:
        Optional free-form detail string (e.g. authentication method used).
    """
    entry = {
        'ts': datetime.now().isoformat(timespec='seconds'),
        'event': event_type,
        'detail': detail,
    }
    try:
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)
        events = _load_events()
        events.append(entry)
        # Keep only the last _MAX_EVENTS
        if len(events) > _MAX_EVENTS:
            events = events[-_MAX_EVENTS:]
        with open(_log_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Never let audit logging crash the app


def _load_events() -> List[dict]:
    """Load existing events from the log file."""
    if not os.path.exists(_log_path):
        return []
    try:
        with open(_log_path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def get_events() -> List[dict]:
    """Return all stored audit events (newest last)."""
    return _load_events()


def clear_events() -> None:
    """Wipe the audit log."""
    try:
        if os.path.exists(_log_path):
            os.remove(_log_path)
    except Exception:
        pass

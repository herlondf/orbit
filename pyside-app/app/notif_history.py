"""notif_history.py — Notification history store (last 50 entries)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

HISTORY_FILE = Path(os.environ.get('APPDATA', '')) / 'Orbit' / 'notif_history.json'


@dataclass
class NotifEntry:
    service_id: str
    service_name: str
    title: str
    body: str
    timestamp: str  # ISO format


_history: List[NotifEntry] = []


def add_notification(service_id: str, service_name: str, title: str, body: str = '') -> None:
    entry = NotifEntry(service_id, service_name, title, body, datetime.now().isoformat())
    _history.insert(0, entry)
    if len(_history) > 50:
        _history.pop()
    _save()


def get_history() -> List[NotifEntry]:
    return list(_history)


def clear_history() -> None:
    global _history
    _history = []
    _save()


def load_history() -> None:
    global _history
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
            _history = [NotifEntry(**e) for e in data]
        except Exception:
            _history = []


def _save() -> None:
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps([e.__dict__ for e in _history], ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    except Exception as e:
        print(f'[notif_history] Save error: {e}')

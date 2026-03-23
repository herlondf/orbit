"""Reading list — save links from webviews for later reading."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class ReadingItem:
    url: str
    title: str
    service_name: str
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False


def _path() -> str:
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(appdata, 'Orbit', 'reading_list.json')


def load_reading_list() -> List[ReadingItem]:
    path = _path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [ReadingItem(**item) for item in data]
    except Exception:
        return []


def save_reading_list(items: List[ReadingItem]):
    path = _path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump([vars(item) for item in items], f, indent=2, ensure_ascii=False)


def add_to_reading_list(url: str, title: str, service_name: str) -> bool:
    items = load_reading_list()
    if any(i.url == url for i in items):
        return False  # already exists
    items.insert(0, ReadingItem(url=url, title=title or url, service_name=service_name))
    items = items[:200]  # keep last 200
    save_reading_list(items)
    return True


def mark_read(url: str):
    items = load_reading_list()
    for item in items:
        if item.url == url:
            item.read = True
    save_reading_list(items)


def remove_item(url: str):
    items = [i for i in load_reading_list() if i.url != url]
    save_reading_list(items)

"""stats.py — Usage time tracking for Orbit services."""
from __future__ import annotations
import json, os, time
from datetime import datetime
from .storage import STORAGE_DIR

_STATS_FILE = os.path.join(STORAGE_DIR, 'stats.json')


def _today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def load_stats() -> dict:
    if not os.path.exists(_STATS_FILE):
        return {}
    try:
        with open(_STATS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_stats(data: dict) -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(_STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_session(service_id: str, service_name: str, seconds: float) -> None:
    """Add `seconds` to today's total for this service."""
    if seconds < 1:
        return
    data = load_stats()
    today = _today()
    if service_id not in data:
        data[service_id] = {'name': service_name, 'days': {}}
    data[service_id]['name'] = service_name  # keep name updated
    data[service_id]['days'][today] = data[service_id]['days'].get(today, 0) + seconds
    save_stats(data)


def get_weekly_totals() -> list[dict]:
    """Return list of {name, total_seconds} sorted by total descending, for last 7 days."""
    from datetime import date, timedelta
    data = load_stats()
    last7 = {(date.today() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)}
    result = []
    for svc_id, info in data.items():
        total = sum(v for d, v in info.get('days', {}).items() if d in last7)
        if total > 0:
            result.append({'id': svc_id, 'name': info.get('name', svc_id), 'total': total})
    return sorted(result, key=lambda x: x['total'], reverse=True)


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, m = divmod(seconds // 60, 60) if seconds >= 3600 else (0, seconds // 60)
    if seconds >= 3600:
        return f'{h}h {m:02d}min'
    elif seconds >= 60:
        return f'{m}min'
    return f'{seconds}s'

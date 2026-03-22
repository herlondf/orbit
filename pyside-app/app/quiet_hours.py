"""quiet_hours.py — Automatic DND schedule based on time range and weekdays."""
from __future__ import annotations

from datetime import datetime


def is_quiet_now(settings: dict) -> bool:
    """Return True if the current time falls within the configured quiet hours."""
    qh = settings.get('quiet_hours', {})
    if not qh.get('enabled', False):
        return False
    now = datetime.now()
    if now.weekday() not in qh.get('days', []):
        return False
    start = qh.get('start', '22:00')
    end = qh.get('end', '08:00')
    sh, sm = map(int, start.split(':'))
    eh, em = map(int, end.split(':'))
    start_mins = sh * 60 + sm
    end_mins = eh * 60 + em
    cur_mins = now.hour * 60 + now.minute
    if start_mins <= end_mins:
        return start_mins <= cur_mins <= end_mins
    else:  # overnight span (e.g. 22:00 → 08:00)
        return cur_mins >= start_mins or cur_mins <= end_mins

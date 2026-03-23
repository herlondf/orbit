"""Automatic workspace switching based on time-of-day schedules."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import json
import os


@dataclass
class WorkspaceRule:
    workspace_id: str
    days: List[int]          # 0=Mon, 6=Sun
    start_hour: int          # 0-23
    start_minute: int = 0
    end_hour: int = 23
    end_minute: int = 59
    enabled: bool = True


@dataclass
class ScheduleConfig:
    rules: List[WorkspaceRule] = field(default_factory=list)
    enabled: bool = False


def get_active_workspace_id(config: ScheduleConfig, workspaces: list) -> Optional[str]:
    """Return workspace_id if any rule matches current time, else None."""
    if not config.enabled or not config.rules:
        return None
    from datetime import datetime
    now = datetime.now()
    weekday = now.weekday()  # 0=Mon
    hour, minute = now.hour, now.minute
    current_minutes = hour * 60 + minute
    for rule in config.rules:
        if not rule.enabled:
            continue
        if weekday not in rule.days:
            continue
        start = rule.start_hour * 60 + rule.start_minute
        end = rule.end_hour * 60 + rule.end_minute
        if start <= current_minutes <= end:
            if any(w.id == rule.workspace_id for w in workspaces):
                return rule.workspace_id
    return None


def _rules_path() -> str:
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(appdata, 'Orbit', 'workspace_schedule.json')


def load_schedule() -> ScheduleConfig:
    path = _rules_path()
    if not os.path.exists(path):
        return ScheduleConfig()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rules = [WorkspaceRule(**r) for r in data.get('rules', [])]
        return ScheduleConfig(rules=rules, enabled=data.get('enabled', False))
    except Exception:
        return ScheduleConfig()


def save_schedule(config: ScheduleConfig):
    path = _rules_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        'enabled': config.enabled,
        'rules': [
            {
                'workspace_id': r.workspace_id,
                'days': r.days,
                'start_hour': r.start_hour,
                'start_minute': r.start_minute,
                'end_hour': r.end_hour,
                'end_minute': r.end_minute,
                'enabled': r.enabled,
            }
            for r in config.rules
        ]
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

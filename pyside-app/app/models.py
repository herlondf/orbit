from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


def new_id(prefix: str = '') -> str:
    uid = str(uuid.uuid4())[:8]
    return f'{prefix}-{uid}' if prefix else uid


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


@dataclass
class Account:
    id: str
    label: str
    url: str
    profile_name: str   # unique key → isolated QWebEngineProfile storage
    notifications: str = 'native'  # 'native' | 'muted'
    authuser: int = 0               # Google account index (0=first, 1=second, …)


@dataclass
class Service:
    id: str
    service_type: str
    name: str
    icon: str           # 2-char abbreviation shown in sidebar
    color: str          # hex colour for icon background
    accounts: List[Account] = field(default_factory=list)
    unread: int = 0
    hibernate_after: Optional[int] = None   # minutes; None = never
    pinned: bool = False
    custom_css: str = ''
    custom_js: str = ''
    zoom: float = 1.0
    notification_sound: str = ''
    incognito: bool = False
    proxy: str = ''
    enabled: bool = True          # Feature: enable/disable service
    tags: List[str] = field(default_factory=list)   # Feature: service tags
    spellcheck: bool = True       # Feature: per-service spellcheck toggle
    preload: bool = False         # Feature: lazy-loading — preload on startup


@dataclass
class ServiceGroup:
    id: str
    name: str
    service_ids: list  # list of service IDs in this group
    collapsed: bool = False


@dataclass
class Workspace:
    id: str
    name: str
    services: List[Service] = field(default_factory=list)
    groups: list = field(default_factory=list)  # list of ServiceGroup
    accent: str = ''  # hex color like '#7c6af7', empty = use global accent

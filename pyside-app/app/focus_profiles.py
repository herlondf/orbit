"""
focus_profiles.py — Focus profile management for Orbit.

Defines pre-set profiles that mute specific service tag groups and
optionally enable Do-Not-Disturb mode.
"""
from __future__ import annotations

from typing import Dict, List

# Built-in focus profiles
PROFILES: Dict[str, dict] = {
    'default':  {'mute_tags': [],           'dnd': False},
    'work':     {'mute_tags': ['personal'], 'dnd': False},
    'personal': {'mute_tags': ['work'],     'dnd': False},
    'off':      {'mute_tags': [],           'dnd': True},
}

PROFILE_LABELS = {
    'default':  '🌐 Padrão',
    'work':     '💼 Trabalho',
    'personal': '🏠 Pessoal',
    'off':      '🔕 Offline',
}

PROFILE_ORDER = ['default', 'work', 'personal', 'off']

_active_profile: str = 'default'


def get_active_profile() -> str:
    """Return the currently active focus profile key."""
    return _active_profile


def set_active_profile(profile: str) -> None:
    """Set the active focus profile."""
    global _active_profile
    if profile in PROFILES:
        _active_profile = profile


def get_muted_tags() -> List[str]:
    """Return the list of tags that should be muted in the active profile."""
    return PROFILES.get(_active_profile, {}).get('mute_tags', [])


def is_dnd_in_profile() -> bool:
    """Return whether the active profile enables DND."""
    return PROFILES.get(_active_profile, {}).get('dnd', False)


def is_service_muted_by_profile(service_tags: List[str]) -> bool:
    """Return True if the service should be muted due to the active focus profile."""
    muted = get_muted_tags()
    if not muted:
        return False
    return any(tag in muted for tag in service_tags)


def cycle_profile() -> str:
    """Cycle to the next profile and return its key."""
    global _active_profile
    current_idx = PROFILE_ORDER.index(_active_profile) if _active_profile in PROFILE_ORDER else 0
    next_idx = (current_idx + 1) % len(PROFILE_ORDER)
    _active_profile = PROFILE_ORDER[next_idx]
    return _active_profile


def load_profile_from_settings(settings: dict) -> None:
    """Load the saved focus profile from the settings dict."""
    global _active_profile
    saved = settings.get('focus_profile', 'default')
    if saved in PROFILES:
        _active_profile = saved


def save_profile_to_settings(settings: dict) -> None:
    """Write the active profile key into the settings dict (caller must persist)."""
    settings['focus_profile'] = _active_profile

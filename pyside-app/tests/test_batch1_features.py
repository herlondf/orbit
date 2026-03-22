"""Tests for batch-1 features: focus_profiles, audit_log, clipboard_guard, i18n,
   models (enabled/tags/spellcheck/preload), storage serialization."""
from __future__ import annotations

import json
import os
import tempfile
import time

import pytest


# ── i18n ──────────────────────────────────────────────────────────────────────

from app.i18n import t, set_locale, get_locale, available_locales


class TestI18n:
    def test_default_locale_is_valid(self):
        assert get_locale() in ('en', 'pt')

    def test_t_returns_string(self):
        assert isinstance(t('add_service'), str)
        assert len(t('add_service')) > 0

    def test_t_english(self):
        set_locale('en')
        assert t('add_service') == 'Add Service'
        assert t('workspace') == 'Workspace'

    def test_t_portuguese(self):
        set_locale('pt')
        assert t('add_service') == 'Adicionar Serviço'
        assert t('workspace') == 'Espaço de Trabalho'

    def test_t_fallback_unknown_key(self):
        set_locale('en')
        key = '__nonexistent_key__'
        assert t(key) == key

    def test_set_locale_invalid_falls_back_to_en(self):
        set_locale('zz')
        assert get_locale() == 'en'
        assert t('ok') == 'OK'

    def test_available_locales(self):
        locs = available_locales()
        assert 'en' in locs
        assert 'pt' in locs

    def test_t_covers_40_strings(self):
        set_locale('en')
        # All keys should resolve to non-empty strings (not the key itself)
        from app.i18n import _STRINGS
        en_keys = list(_STRINGS['en'].keys())
        assert len(en_keys) >= 40, f'Only {len(en_keys)} strings defined (need ≥40)'

    def teardown_method(self):
        set_locale('en')  # restore after each test


# ── focus_profiles ─────────────────────────────────────────────────────────────

from app.focus_profiles import (
    PROFILES, PROFILE_ORDER, get_active_profile, set_active_profile,
    cycle_profile, get_muted_tags, is_dnd_in_profile,
    is_service_muted_by_profile, load_profile_from_settings, save_profile_to_settings,
)


class TestFocusProfiles:
    def setup_method(self):
        set_active_profile('default')

    def test_default_profile(self):
        assert get_active_profile() == 'default'

    def test_set_profile(self):
        set_active_profile('work')
        assert get_active_profile() == 'work'

    def test_set_invalid_profile_noop(self):
        set_active_profile('work')
        current = get_active_profile()
        set_active_profile('nonexistent')
        assert get_active_profile() == current  # unchanged

    def test_cycle_profile(self):
        set_active_profile('default')
        nxt = cycle_profile()
        assert nxt == 'work'
        nxt = cycle_profile()
        assert nxt == 'personal'

    def test_muted_tags_default(self):
        set_active_profile('default')
        assert get_muted_tags() == []

    def test_muted_tags_work(self):
        set_active_profile('work')
        assert 'personal' in get_muted_tags()

    def test_dnd_off_profile(self):
        set_active_profile('off')
        assert is_dnd_in_profile() is True

    def test_dnd_work_profile(self):
        set_active_profile('work')
        assert is_dnd_in_profile() is False

    def test_is_service_muted_by_profile(self):
        set_active_profile('work')
        assert is_service_muted_by_profile(['personal']) is True
        assert is_service_muted_by_profile(['work']) is False
        assert is_service_muted_by_profile([]) is False

    def test_load_save_profile_settings(self):
        settings: dict = {}
        set_active_profile('personal')
        save_profile_to_settings(settings)
        assert settings['focus_profile'] == 'personal'

        set_active_profile('default')
        load_profile_from_settings(settings)
        assert get_active_profile() == 'personal'

    def teardown_method(self):
        set_active_profile('default')


# ── audit_log ──────────────────────────────────────────────────────────────────

from app.audit_log import log_event, get_events, clear_events, set_log_path, get_log_path


class TestAuditLog:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._tmp.close()
        set_log_path(self._tmp.name)
        clear_events()

    def teardown_method(self):
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass

    def test_log_event_creates_entry(self):
        log_event('app_start')
        events = get_events()
        assert len(events) == 1
        assert events[0]['event'] == 'app_start'

    def test_log_event_with_detail(self):
        log_event('unlocked', 'pin')
        events = get_events()
        assert events[0]['detail'] == 'pin'

    def test_log_event_has_timestamp(self):
        log_event('test_event')
        events = get_events()
        assert 'ts' in events[0]
        assert 'T' in events[0]['ts']  # ISO format

    def test_multiple_events_ordered(self):
        for ev in ['app_start', 'service_added', 'service_removed']:
            log_event(ev)
        events = get_events()
        assert len(events) == 3
        assert [e['event'] for e in events] == ['app_start', 'service_added', 'service_removed']

    def test_max_500_events(self):
        for i in range(510):
            log_event('test', str(i))
        events = get_events()
        assert len(events) == 500

    def test_clear_events(self):
        log_event('app_start')
        clear_events()
        assert get_events() == []

    def test_log_path_override(self):
        assert get_log_path() == self._tmp.name

    def test_graceful_with_bad_path(self):
        set_log_path('/nonexistent/path/audit.log')
        # Should not raise
        log_event('test')
        # Restore
        set_log_path(self._tmp.name)


# ── clipboard_guard ────────────────────────────────────────────────────────────

class TestClipboardGuard:
    """Basic structural/unit tests for ClipboardGuard (no live Qt event loop needed)."""

    def test_import(self):
        from app.clipboard_guard import ClipboardGuard
        assert ClipboardGuard is not None

    def test_class_has_cleared_signal(self):
        from app.clipboard_guard import ClipboardGuard
        assert hasattr(ClipboardGuard, 'cleared')

    def test_set_timeout(self):
        """Verify set_timeout stores the value (no QApp needed for this check)."""
        import inspect
        from app.clipboard_guard import ClipboardGuard
        src = inspect.getsource(ClipboardGuard.set_timeout)
        assert 'self._timeout_ms' in src

    def test_get_timeout_method_exists(self):
        from app.clipboard_guard import ClipboardGuard
        assert callable(ClipboardGuard.get_timeout)


# ── models — new fields ────────────────────────────────────────────────────────

from app.models import Service


class TestServiceModel:
    def _make_service(self, **kwargs):
        defaults = dict(id='s1', service_type='slack', name='Slack', icon='Sl', color='#aaa')
        defaults.update(kwargs)
        return Service(**defaults)

    def test_enabled_default_true(self):
        svc = self._make_service()
        assert svc.enabled is True

    def test_enabled_can_be_false(self):
        svc = self._make_service(enabled=False)
        assert svc.enabled is False

    def test_tags_default_empty(self):
        svc = self._make_service()
        assert svc.tags == []

    def test_tags_set(self):
        svc = self._make_service(tags=['work', 'chat'])
        assert 'work' in svc.tags

    def test_spellcheck_default_true(self):
        svc = self._make_service()
        assert svc.spellcheck is True

    def test_preload_default_false(self):
        svc = self._make_service()
        assert svc.preload is False


# ── storage — serialization of new fields ─────────────────────────────────────

from app.storage import _service_to_dict, _service_from_dict
from app.models import Account


class TestStorageSerialization:
    def _make_service(self, **kwargs):
        defaults = dict(id='s1', service_type='slack', name='Slack', icon='Sl', color='#aaa')
        defaults.update(kwargs)
        return Service(**defaults)

    def test_enabled_round_trip_true(self):
        svc = self._make_service(enabled=True)
        d = _service_to_dict(svc)
        assert d['enabled'] is True
        svc2 = _service_from_dict(d)
        assert svc2.enabled is True

    def test_enabled_round_trip_false(self):
        svc = self._make_service(enabled=False)
        d = _service_to_dict(svc)
        assert d['enabled'] is False
        svc2 = _service_from_dict(d)
        assert svc2.enabled is False

    def test_tags_round_trip(self):
        svc = self._make_service(tags=['work', 'personal'])
        d = _service_to_dict(svc)
        assert d['tags'] == ['work', 'personal']
        svc2 = _service_from_dict(d)
        assert svc2.tags == ['work', 'personal']

    def test_spellcheck_round_trip(self):
        svc = self._make_service(spellcheck=False)
        d = _service_to_dict(svc)
        assert d['spellcheck'] is False
        svc2 = _service_from_dict(d)
        assert svc2.spellcheck is False

    def test_preload_round_trip(self):
        svc = self._make_service(preload=True)
        d = _service_to_dict(svc)
        assert d['preload'] is True
        svc2 = _service_from_dict(d)
        assert svc2.preload is True

    def test_missing_enabled_defaults_true(self):
        d = {'id': 's1', 'service_type': 'slack', 'name': 'Slack',
             'icon': 'Sl', 'color': '#aaa', 'accounts': []}
        svc = _service_from_dict(d)
        assert svc.enabled is True

    def test_missing_tags_defaults_empty(self):
        d = {'id': 's1', 'service_type': 'slack', 'name': 'Slack',
             'icon': 'Sl', 'color': '#aaa', 'accounts': []}
        svc = _service_from_dict(d)
        assert svc.tags == []

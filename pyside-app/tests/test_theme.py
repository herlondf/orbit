"""Tests for app.theme — dark/light tokens and system detection."""
import pytest


def test_is_system_dark_does_not_raise():
    from app.theme import _is_system_dark
    # Should not raise even if winreg is not available or key missing
    result = _is_system_dark()
    assert isinstance(result, bool)


def test_light_tokens_returns_color_tokens():
    from app.theme import light_tokens, ColorTokens
    tokens = light_tokens('#7c6af7')
    assert isinstance(tokens, ColorTokens)
    assert tokens.bg_base  # non-empty
    assert tokens.accent == '#7c6af7'


def test_dark_tokens_returns_color_tokens():
    from app.theme import dark_tokens, ColorTokens
    tokens = dark_tokens('#7c6af7')
    assert isinstance(tokens, ColorTokens)
    assert tokens.accent == '#7c6af7'


def test_get_tokens_dark_mode():
    from app.theme import get_tokens
    tokens = get_tokens('dark', '#7c6af7')
    assert tokens.bg_base == '#16161a'


def test_get_tokens_light_mode():
    from app.theme import get_tokens
    tokens = get_tokens('light', '#7c6af7')
    assert tokens.bg_base == '#f4f4f8'


def test_get_tokens_system_mode_returns_tokens():
    from app.theme import get_tokens, ColorTokens
    tokens = get_tokens('system', '#7c6af7')
    assert isinstance(tokens, ColorTokens)


def test_darken():
    from app.theme import _darken
    darker = _darken('#ffffff', 18)
    assert darker.startswith('#')
    assert darker != '#ffffff'


def test_alpha():
    from app.theme import _alpha
    result = _alpha('#7c6af7', 28)
    assert result.startswith('rgba(')


def test_color_tokens_qss():
    from app.theme import dark_tokens
    tokens = dark_tokens('#7c6af7')
    qss = tokens.qss()
    assert isinstance(qss, str)
    assert len(qss) > 100
    assert '#7c6af7' in qss


def test_accents_dict_has_entries():
    from app.theme import ACCENTS
    assert 'Iris' in ACCENTS
    assert ACCENTS['Iris'].startswith('#')

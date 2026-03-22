"""Tests for app.lock_screen — PIN hashing and LockScreen widget."""
import pytest


def test_hash_pin_returns_hex_string():
    from app.lock_screen import hash_pin
    result = hash_pin('1234')
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 = 64 hex chars
    assert all(c in '0123456789abcdef' for c in result)


def test_hash_pin_is_deterministic():
    from app.lock_screen import hash_pin
    assert hash_pin('1234') == hash_pin('1234')


def test_hash_pin_different_pins():
    from app.lock_screen import hash_pin
    assert hash_pin('1234') != hash_pin('1235')
    assert hash_pin('0000') != hash_pin('9999')


def test_hash_pin_empty():
    from app.lock_screen import hash_pin
    result = hash_pin('')
    assert len(result) == 64


def test_lock_screen_creates(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)
    assert widget is not None


def test_lock_screen_correct_pin_emits_unlocked(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.unlocked, timeout=1000):
        for digit in '1234':
            widget._on_key(digit)


def test_lock_screen_wrong_pin_shows_error(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    for digit in '9999':
        widget._on_key(digit)

    assert widget._error.text() != ''
    assert widget._entry == ''


def test_lock_screen_wrong_pin_clears_entry(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    for digit in '5678':
        widget._on_key(digit)

    assert widget._entry == ''


def test_lock_screen_backspace(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    widget._on_key('1')
    widget._on_key('2')
    widget._on_key('⌫')
    assert widget._entry == '1'


def test_lock_screen_backspace_on_empty(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    widget._on_key('⌫')
    assert widget._entry == ''


def test_lock_screen_reset(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    widget._on_key('9')
    widget._on_key('9')
    widget.reset()
    assert widget._entry == ''
    assert widget._error.text() == ''


def test_lock_screen_max_4_digits(qtbot):
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    # Type more than 4 digits (without auto-verify completing)
    # After 4 digits auto-verify fires if matching, use a non-matching PIN
    widget._pin_hash = 'never_match'
    for digit in '12345678':
        widget._on_key(digit)
    # Entry should not exceed 4 chars at any point (auto-verify clears it)
    assert len(widget._entry) <= 4


def test_lock_screen_check_mark_key(qtbot):
    """Pressing ✓ with wrong pin should show error."""
    from app.lock_screen import LockScreen, hash_pin
    pin_hash = hash_pin('1234')
    widget = LockScreen(pin_hash)
    qtbot.addWidget(widget)

    widget._on_key('1')
    widget._on_key('2')
    widget._on_key('3')
    widget._on_key('✓')
    assert widget._error.text() != ''

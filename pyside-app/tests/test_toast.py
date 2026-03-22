"""Tests for app.toast — Toast notification widget."""
import pytest


def test_toast_manager_show(qtbot):
    """ToastManager.show() creates a _Toast widget without crashing."""
    from app.toast import ToastManager, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    initial_count = len(_active_toasts)
    ToastManager.show(parent, 'Test message', 'info', duration=100)
    assert len(_active_toasts) == initial_count + 1
    # Clean up
    _active_toasts[-1]._cleanup()


def test_toast_info_kind(qtbot):
    from app.toast import _Toast, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    t = _Toast(parent, 'Info message', 'info', duration=100)
    assert t in _active_toasts
    t._cleanup()


def test_toast_success_kind(qtbot):
    from app.toast import _Toast, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    t = _Toast(parent, 'Success!', 'success', duration=100)
    assert t in _active_toasts
    t._cleanup()


def test_toast_error_kind(qtbot):
    from app.toast import _Toast, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    t = _Toast(parent, 'Error occurred', 'error', duration=100)
    assert t in _active_toasts
    t._cleanup()


def test_toast_warning_kind(qtbot):
    from app.toast import _Toast, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    t = _Toast(parent, 'Warning!', 'warning', duration=100)
    assert t in _active_toasts
    t._cleanup()


def test_toast_cleanup_removes_from_list(qtbot):
    from app.toast import _Toast, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    t = _Toast(parent, 'Test', 'info', duration=100)
    assert t in _active_toasts
    t._cleanup()
    assert t not in _active_toasts


def test_toast_start_fade(qtbot):
    from app.toast import _Toast, _active_toasts
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    parent.resize(800, 600)
    parent.show()
    qtbot.addWidget(parent)

    t = _Toast(parent, 'Test', 'info', duration=100)
    t._start_fade()  # Should not raise
    t._cleanup()


def test_toast_colors_dict():
    from app.toast import _COLORS
    for kind in ('info', 'success', 'error', 'warning'):
        assert kind in _COLORS
        bg, fg = _COLORS[kind]
        assert bg.startswith('#')
        assert fg.startswith('#')


def test_toast_icons_dict():
    from app.toast import _ICONS
    for kind in ('info', 'success', 'error', 'warning'):
        assert kind in _ICONS
        assert _ICONS[kind]  # non-empty string

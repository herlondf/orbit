"""Tests for app.hover_effect — hover opacity animation."""
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QEnterEvent


def test_apply_hover_effect(qtbot):
    from app.hover_effect import apply_hover_effect
    from PySide6.QtWidgets import QPushButton
    btn = QPushButton("Test")
    qtbot.addWidget(btn)
    anim = apply_hover_effect(btn)
    assert anim is not None


def test_hover_anim_init(qtbot):
    from app.hover_effect import _HoverAnim
    from PySide6.QtWidgets import QLabel
    lbl = QLabel("Hello")
    qtbot.addWidget(lbl)
    h = _HoverAnim(lbl, hover_opacity=1.0, normal_opacity=0.5)
    assert h._hover_opacity == 1.0
    assert h._normal_opacity == 0.5


def test_hover_effect_animate(qtbot):
    from app.hover_effect import _HoverAnim
    from PySide6.QtWidgets import QLabel
    lbl = QLabel()
    qtbot.addWidget(lbl)
    h = _HoverAnim(lbl)
    h._animate(1.0)
    h._animate(0.5)


def test_hover_effect_enter_leave_events(qtbot):
    from app.hover_effect import apply_hover_effect
    from PySide6.QtWidgets import QPushButton
    btn = QPushButton()
    qtbot.addWidget(btn)
    apply_hover_effect(btn)
    btn.enterEvent(QEnterEvent(QPoint(0, 0), QPoint(0, 0), QPoint(0, 0)))
    btn.leaveEvent(QEvent(QEvent.Type.Leave))

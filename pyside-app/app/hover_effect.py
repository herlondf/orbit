"""Smooth hover opacity animation for any QWidget."""
from __future__ import annotations
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QObject, QByteArray
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect


class _HoverAnim(QObject):
    def __init__(self, widget: QWidget, hover_opacity: float = 1.0, normal_opacity: float = 0.75):
        super().__init__(widget)
        self._effect = QGraphicsOpacityEffect(widget)
        self._effect.setOpacity(normal_opacity)
        widget.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, QByteArray(b"opacity"), self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._hover_opacity = hover_opacity
        self._normal_opacity = normal_opacity

        # Monkey-patch enter/leave events
        orig_enter = widget.enterEvent
        orig_leave = widget.leaveEvent

        def enter(e):
            self._animate(hover_opacity)
            orig_enter(e)

        def leave(e):
            self._animate(normal_opacity)
            orig_leave(e)

        widget.enterEvent = enter
        widget.leaveEvent = leave

    def _animate(self, target: float):
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(target)
        self._anim.start()


def apply_hover_effect(widget: QWidget, hover: float = 1.0, normal: float = 0.75) -> _HoverAnim:
    """Apply a smooth opacity hover animation to widget. Returns the animator (keep reference)."""
    return _HoverAnim(widget, hover, normal)

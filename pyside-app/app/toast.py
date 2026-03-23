"""Bottom-right toast notifications with fade-out animation."""
from __future__ import annotations
from typing import Literal
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QByteArray, QPoint
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect

ToastKind = Literal['info', 'success', 'error', 'warning']

_COLORS: dict[ToastKind, tuple[str, str]] = {
    'info':    ('#1565C0', '#90CAF9'),
    'success': ('#1B5E20', '#A5D6A7'),
    'error':   ('#B71C1C', '#EF9A9A'),
    'warning': ('#E65100', '#FFCC80'),
}
_ICONS: dict[ToastKind, str] = {
    'info': 'ℹ', 'success': '✓', 'error': '✕', 'warning': '⚠',
}

_active_toasts: list['_Toast'] = []


class _Toast(QWidget):
    def __init__(self, parent: QWidget, message: str, kind: ToastKind = 'info', duration: int = 3500):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        bg, fg = _COLORS.get(kind, _COLORS['info'])
        icon = _ICONS.get(kind, 'ℹ')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f'color: {fg}; font-size: 16px; background: transparent;')
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f'color: {fg}; font-size: 12px; background: transparent;')
        msg_lbl.setWordWrap(True)
        msg_lbl.setMaximumWidth(300)
        layout.addWidget(msg_lbl)

        self.setStyleSheet(
            f'QWidget {{ background-color: {bg}; border-radius: 8px;'
            f' border: 1px solid {fg}44; }}'
        )

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

        self._fade = QPropertyAnimation(self._effect, QByteArray(b'opacity'), self)
        self._fade.setDuration(400)
        self._fade.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._cleanup)

        self.adjustSize()
        self._reposition()

        QTimer.singleShot(duration, self._start_fade)
        _active_toasts.append(self)
        self.show()

    def _reposition(self):
        if not self.parent():
            return
        parent: QWidget = self.parent()
        pr = parent.rect()
        margin = 16
        stack_offset = sum(t.height() + 8 for t in _active_toasts if t is not self and t.isVisible())
        x = pr.right() - self.width() - margin
        y = pr.bottom() - self.height() - margin - stack_offset
        self.move(parent.mapToGlobal(QPoint(x, y)))

    def _start_fade(self):
        self._fade.start()

    def _cleanup(self):
        if self in _active_toasts:
            _active_toasts.remove(self)
        self.hide()
        self.deleteLater()


class ToastManager:
    @staticmethod
    def show(parent: QWidget, message: str, kind: ToastKind = 'info', duration: int = 3500):
        _Toast(parent, message, kind, duration)

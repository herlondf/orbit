"""Pulsating skeleton loader widget for loading states."""
from __future__ import annotations
from PySide6.QtCore import (Qt, QPropertyAnimation, QEasingCurve, QByteArray)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QGraphicsOpacityEffect
from PySide6.QtGui import QColor, QPainter, QColor, QPainter


class _SkeletonBar(QFrame):
    def __init__(self, width_pct: float = 1.0, height: int = 14, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._width_pct = width_pct
        self.setStyleSheet('background-color: transparent; border: none;')
        self._color = QColor('#3e3e52')

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        w = int(self.width() * self._width_pct)
        p.drawRoundedRect(0, 0, w, self.height(), 4, 4)


class SkeletonWidget(QWidget):
    """Pulsating skeleton loading bars. Show while content loads, hide when done."""

    def __init__(self, lines: int = 5, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        widths = [1.0, 0.85, 0.95, 0.70, 0.80, 0.90, 0.75, 0.60]
        for i in range(lines):
            bar = _SkeletonBar(width_pct=widths[i % len(widths)], height=14)
            layout.addWidget(bar)

        layout.addStretch()

        # Pulse animation
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)

        self._pulse = QPropertyAnimation(self._effect, QByteArray(b'opacity'), self)
        self._pulse.setDuration(1000)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse.setLoopCount(-1)
        self._pulse.setKeyValueAt(0, 0.3)
        self._pulse.setKeyValueAt(0.5, 0.7)
        self._pulse.setKeyValueAt(1, 0.3)
        self._pulse.start()

    def stop(self):
        self._pulse.stop()

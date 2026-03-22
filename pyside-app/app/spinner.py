"""Rotating arc spinner for in-progress operations."""
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor


class Spinner(QWidget):
    def __init__(self, size: int = 20, color: str = '#7c6af7', stroke: int = 3, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._stroke = stroke
        self._angle = 0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # ~60fps

    def _rotate(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, e):  # pragma: no cover
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self._color, self._stroke)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        margin = self._stroke
        rect = QRect(margin, margin, self.width() - 2*margin, self.height() - 2*margin)
        p.drawArc(rect, self._angle * 16, 270 * 16)

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def stop(self):
        self._timer.stop()

    def start(self):
        self._timer.start(16)

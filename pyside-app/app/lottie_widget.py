"""LottieLabel — lightweight Lottie animation player using rlottie-python.

Pre-renders all frames to QPixmap at construction time (very fast at small
sizes) then cycles them with a QTimer.  No QML, no QWebEngine overhead.
"""
from __future__ import annotations

import os
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


def _render_frames(path: str, size: int, skip: int) -> List[QPixmap]:
    """Return a list of QPixmap frames rendered from a Lottie JSON file."""
    try:
        import rlottie_python as rl

        anim = rl.LottieAnimation.from_file(path)
        total = anim.lottie_animation_get_totalframe()
        frames: List[QPixmap] = []
        for i in range(0, total, max(1, skip)):
            pil = anim.render_pillow_frame(i, width=size, height=size)
            raw = pil.tobytes('raw', 'RGBA')
            img = QImage(raw, size, size, size * 4, QImage.Format.Format_RGBA8888)
            frames.append(QPixmap.fromImage(img.copy()))
        return frames
    except Exception:
        return []


class LottieLabel(QLabel):
    """QLabel that plays a Lottie animation by cycling pre-rendered frames."""

    def __init__(
        self,
        path: str,
        size: int = 40,
        fps: float = 30.0,
        skip_frames: int = 2,
        parent=None,
    ):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(size, size)
        self.setStyleSheet('background: transparent;')

        self._frames = _render_frames(path, size, skip_frames)
        self._idx = 0

        if self._frames:
            self.setPixmap(self._frames[0])
            self._timer = QTimer(self)
            self._timer.setInterval(max(16, int(1000 / fps)))
            self._timer.timeout.connect(self._next_frame)
            self._timer.start()

    def _next_frame(self) -> None:
        if not self._frames:
            return
        self._idx = (self._idx + 1) % len(self._frames)
        self.setPixmap(self._frames[self._idx])

    def stop(self) -> None:
        if hasattr(self, '_timer'):
            self._timer.stop()

    def start(self) -> None:
        if hasattr(self, '_timer'):
            self._timer.start()

    @staticmethod
    def lottie_path() -> str:
        """Return the absolute path to the bundled Orbit Brands Lottie file."""
        base = getattr(__import__('sys'), '_MEIPASS', None)
        if base:
            p = os.path.join(base, 'assets', 'Orbit Brands.json')
        else:
            # Dev layout: pyside-app/app/lottie_widget.py → project root is 3 levels up
            root = os.path.dirname(  # project root
                os.path.dirname(  # pyside-app/
                    os.path.dirname(__file__)  # pyside-app/app/
                )
            )
            p = os.path.join(root, 'assets', 'Orbit Brands.json')
            if not os.path.exists(p):
                # Fallback to Aurora Loader
                p = os.path.join(root, 'assets', 'Aurora Loader.json')
        return p

"""
clipboard_guard.py — Auto-clear clipboard after inactivity for Orbit.

Monitors clipboard changes and clears the clipboard content after a
configurable timeout to reduce accidental data exposure.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication


class ClipboardGuard(QObject):
    """
    Monitors the system clipboard and clears it after *timeout_ms* milliseconds
    of inactivity (no further changes).

    Parameters
    ----------
    app:
        The running QApplication instance (used to access the clipboard).
    timeout_ms:
        Milliseconds after the last clipboard change before content is cleared.
        Pass 0 to disable auto-clearing.

    Signals
    -------
    cleared:
        Emitted after the clipboard has been auto-cleared.
    """

    cleared = Signal()

    def __init__(self, app: QApplication, timeout_ms: int = 30_000, parent=None):
        super().__init__(parent)
        self._app = app
        self._timeout_ms = timeout_ms
        self._last_text: str = ''

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        clipboard = app.clipboard()
        clipboard.dataChanged.connect(self._on_clipboard_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_timeout(self, ms: int) -> None:
        """Change the auto-clear timeout. Pass 0 to disable."""
        self._timeout_ms = ms
        if ms == 0:
            self._timer.stop()

    def get_timeout(self) -> int:
        """Return the current timeout in milliseconds."""
        return self._timeout_ms

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_clipboard_changed(self) -> None:
        """Called whenever clipboard content changes."""
        if self._timeout_ms <= 0:
            return
        clipboard = self._app.clipboard()
        self._last_text = clipboard.text()
        # Restart the timer on each change
        self._timer.stop()
        if self._last_text:  # only arm when there is content
            self._timer.start(self._timeout_ms)

    def _on_timeout(self) -> None:
        """Clear the clipboard if content hasn't changed since the timer started."""
        clipboard = self._app.clipboard()
        current = clipboard.text()
        if current and current == self._last_text:
            clipboard.clear()
            self._last_text = ''
            self.cleared.emit()

import hashlib
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
    QPushButton, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class LockScreen(QWidget):
    unlocked = Signal()

    def __init__(self, pin_hash: str, parent=None):
        super().__init__(parent)
        self._pin_hash = pin_hash
        self._entry = ''
        self._build()
        self.setObjectName('lockScreen')
        self.setStyleSheet(
            '#lockScreen { background: rgba(30,30,46,0.97); }'
        )

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        logo = QLabel('🔒')
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet('font-size:56px;')
        layout.addWidget(logo)

        title = QLabel('Orbit bloqueado')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size:18px;font-weight:600;color:#cdd6f4;')
        layout.addWidget(title)

        self._dots = QLabel('○ ○ ○ ○')
        self._dots.setAlignment(Qt.AlignCenter)
        self._dots.setStyleSheet('font-size:24px;letter-spacing:12px;color:#cdd6f4;')
        layout.addWidget(self._dots)

        self._error = QLabel('')
        self._error.setAlignment(Qt.AlignCenter)
        self._error.setStyleSheet('color:#f38ba8;font-size:12px;')
        layout.addWidget(self._error)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(12)
        nums = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '⌫', '0', '✓']
        for i, n in enumerate(nums):
            btn = QPushButton(n)
            btn.setFixedSize(72, 72)
            btn.setStyleSheet(
                'font-size:20px;border-radius:36px;'
                'background:#313244;color:#cdd6f4;border:none;'
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, x=n: self._on_key(x))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addWidget(grid_w, 0, Qt.AlignCenter)

    def _update_dots(self):
        filled = '● ' * len(self._entry)
        empty = '○ ' * (4 - len(self._entry))
        self._dots.setText((filled + empty).strip())

    def _on_key(self, key: str):
        if key == '⌫':
            self._entry = self._entry[:-1]
            self._error.setText('')
        elif key == '✓':
            self._verify()
        elif len(self._entry) < 4 and key.isdigit():
            self._entry += key
            if len(self._entry) == 4:
                self._verify()
        self._update_dots()

    def _verify(self):
        h = hashlib.sha256(self._entry.encode()).hexdigest()
        if h == self._pin_hash:
            self.unlocked.emit()
        else:
            self._error.setText('PIN incorreto. Tente novamente.')
            self._entry = ''
            self._update_dots()

    def reset(self):
        self._entry = ''
        self._error.setText('')
        self._update_dots()


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

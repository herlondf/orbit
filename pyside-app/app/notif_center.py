"""notif_center.py — Slide-in notification center panel."""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QComboBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QSize
from PySide6.QtGui import QFont, QColor


class NotifEntryWidget(QFrame):
    """A single notification entry."""

    def __init__(self, title: str, body: str, service: str = '', ts: str = '', parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            'NotifEntryWidget { background: #313244; border-radius: 8px; '
            'border: 1px solid #45475a; margin: 2px 0; }'
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        header = QHBoxLayout()
        svc_lbl = QLabel(service or 'Orbit')
        svc_lbl.setStyleSheet('font-size: 10px; color: #6c7086; font-weight: bold;')
        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet('font-size: 10px; color: #6c7086;')
        header.addWidget(svc_lbl)
        header.addStretch()
        header.addWidget(ts_lbl)
        layout.addLayout(header)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet('font-size: 12px; font-weight: bold; color: #cdd6f4;')
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        if body:
            body_lbl = QLabel(body)
            body_lbl.setStyleSheet('font-size: 11px; color: #a6adc8;')
            body_lbl.setWordWrap(True)
            layout.addWidget(body_lbl)


class NotificationCenter(QWidget):
    """Slide-in notification center panel."""

    PANEL_WIDTH = 320
    closed = Signal()

    def __init__(self, parent: QWidget, accent: str = '#7c6af7'):
        super().__init__(parent)
        self._accent = accent
        self._open = False
        self._anim: QPropertyAnimation | None = None
        self._build()
        self.hide()

    def _build(self):
        self.setObjectName('notifCenter')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            '#notifCenter { background: #1e1e2e; border-left: 1px solid #313244; }'
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet('background: #181825; border-bottom: 1px solid #313244;')
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 12, 0)

        title_lbl = QLabel('🔔 Notificações')
        title_lbl.setStyleSheet('font-size: 14px; font-weight: bold; color: #cdd6f4;')
        h_layout.addWidget(title_lbl)
        h_layout.addStretch()

        close_btn = QPushButton('✕')
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            'QPushButton { background: transparent; color: #6c7086; border: none; font-size: 16px; }'
            'QPushButton:hover { color: #cdd6f4; }'
        )
        close_btn.clicked.connect(self.close_panel)
        h_layout.addWidget(close_btn)
        layout.addWidget(header)

        # Filter bar
        filter_bar = QWidget()
        filter_bar.setStyleSheet('background: #181825; border-bottom: 1px solid #313244;')
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(16, 8, 16, 8)
        fb_layout.setSpacing(8)

        filter_lbl = QLabel('Filtrar:')
        filter_lbl.setStyleSheet('font-size: 11px; color: #6c7086;')
        fb_layout.addWidget(filter_lbl)

        self._filter_combo = QComboBox()
        self._filter_combo.addItem('Todos os serviços')
        self._filter_combo.setStyleSheet(
            'QComboBox { background: #313244; color: #cdd6f4; border: 1px solid #45475a; '
            'border-radius: 4px; padding: 2px 8px; font-size: 11px; }'
        )
        fb_layout.addWidget(self._filter_combo, 1)

        clear_btn = QPushButton('Limpar tudo')
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet(
            'QPushButton { background: transparent; color: #6c7086; border: none; font-size: 11px; }'
            'QPushButton:hover { color: #f38ba8; }'
        )
        clear_btn.clicked.connect(self._clear_all)
        fb_layout.addWidget(clear_btn)
        layout.addWidget(filter_bar)

        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea { border: none; background: #1e1e2e; }')

        self._notif_container = QWidget()
        self._notif_layout = QVBoxLayout(self._notif_container)
        self._notif_layout.setContentsMargins(12, 12, 12, 12)
        self._notif_layout.setSpacing(6)
        self._notif_layout.addStretch()

        scroll.setWidget(self._notif_container)
        layout.addWidget(scroll, 1)

        self._empty_lbl = QLabel('Nenhuma notificação')
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet('font-size: 13px; color: #6c7086; padding: 20px;')
        layout.addWidget(self._empty_lbl)

    def set_accent(self, accent: str):
        self._accent = accent

    def update_services(self, service_names: list):
        """Update the service filter combo."""
        self._filter_combo.clear()
        self._filter_combo.addItem('Todos os serviços')
        for name in service_names:
            self._filter_combo.addItem(name)

    def add_notification(self, title: str, body: str = '', service: str = '', ts: str = ''):
        """Add a notification entry to the panel."""
        entry = NotifEntryWidget(title, body, service, ts, self._notif_container)
        # Insert before the stretch at the end
        count = self._notif_layout.count()
        self._notif_layout.insertWidget(count - 1, entry)
        self._empty_lbl.hide()

    def _clear_all(self):
        while self._notif_layout.count() > 1:
            item = self._notif_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._empty_lbl.show()

    def toggle(self):
        if self._open:
            self.close_panel()
        else:
            self.open_panel()

    def open_panel(self):  # pragma: no cover
        if self._open:
            return
        parent = self.parent()
        if parent:
            ph = parent.height()
            self.setGeometry(parent.width(), 0, self.PANEL_WIDTH, ph)
            self.show()
            self.raise_()
            self._anim = QPropertyAnimation(self, b'geometry')
            self._anim.setDuration(250)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.setStartValue(QRect(parent.width(), 0, self.PANEL_WIDTH, ph))
            self._anim.setEndValue(QRect(parent.width() - self.PANEL_WIDTH, 0, self.PANEL_WIDTH, ph))
            self._anim.start()
        self._open = True

    def close_panel(self):  # pragma: no cover
        if not self._open:
            return
        parent = self.parent()
        if parent:
            ph = parent.height()
            self._anim = QPropertyAnimation(self, b'geometry')
            self._anim.setDuration(200)
            self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
            self._anim.setStartValue(QRect(parent.width() - self.PANEL_WIDTH, 0, self.PANEL_WIDTH, ph))
            self._anim.setEndValue(QRect(parent.width(), 0, self.PANEL_WIDTH, ph))
            self._anim.finished.connect(self.hide)
            self._anim.start()
        self._open = False
        self.closed.emit()

    def is_open(self) -> bool:
        return self._open

    def resizeEvent(self, event):  # pragma: no cover
        super().resizeEvent(event)

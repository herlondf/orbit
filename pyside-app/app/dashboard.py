"""dashboard.py — Rich summary dashboard shown when no service is selected."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .models import Service
from .stats import fmt_duration, get_weekly_totals


class ServiceCard(QFrame):
    clicked = Signal(str)  # service_id

    def __init__(self, svc: Service, parent=None):
        super().__init__(parent)
        self.setObjectName('serviceCard')
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(160, 120)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel(svc.icon)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet('font-size:32px;')
        layout.addWidget(icon)

        name = QLabel(svc.name)
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet('font-weight:600;')
        layout.addWidget(name)

        if svc.unread:
            badge = QLabel(f'🔴 {svc.unread} não lidos')
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet('color:#f38ba8;font-size:11px;')
            layout.addWidget(badge)

    def mousePressEvent(self, e):
        self.clicked.emit(self.property('svc_id'))


class DashboardWidget(QWidget):
    service_clicked = Signal(str)  # service_id

    def __init__(self, services: List[Service], parent=None):
        super().__init__(parent)
        self._services = services
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(32, 32, 32, 32)
        self._layout.setSpacing(24)
        self._build()

    def _build(self):
        layout = self._layout

        header = QLabel('🐙 OctoChat')
        header.setObjectName('wTitle')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Weekly stats summary
        totals = get_weekly_totals()
        if totals:
            top = totals[0]
            stat_lbl = QLabel(
                f'Serviço mais usado: {top["name"]} — {fmt_duration(top["total"])} esta semana'
            )
            stat_lbl.setAlignment(Qt.AlignCenter)
            stat_lbl.setStyleSheet('color:#a6adc8;font-size:12px;')
            layout.addWidget(stat_lbl)

        # Service cards grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(16)

        cols = 4
        for i, svc in enumerate(self._services):
            card = ServiceCard(svc)
            card.setProperty('svc_id', svc.id)
            card.clicked.connect(self.service_clicked)
            grid.addWidget(card, i // cols, i % cols)

        scroll.setWidget(grid_w)
        layout.addWidget(scroll)

    def refresh(self, services: List[Service]):
        self._services = services
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build()

from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QStackedWidget, QGridLayout, QFrame)
from PySide6.QtCore import Qt, Signal


class OnboardingDialog(QDialog):  # pragma: no cover
    theme_chosen = Signal(str)    # 'dark' / 'light' / 'system'
    service_chosen = Signal(str)  # service_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Bem-vindo ao Orbit')
        self.setFixedSize(540, 440)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._step = 0
        self._chosen_theme = 'dark'
        self._chosen_service = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._make_step0())
        self._stack.addWidget(self._make_step1())
        self._stack.addWidget(self._make_step2())
        self._stack.addWidget(self._make_step3())

        nav = QWidget()
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(16, 8, 16, 16)
        self._back_btn = QPushButton('← Voltar')
        self._back_btn.clicked.connect(self._prev)
        self._back_btn.setVisible(False)
        self._next_btn = QPushButton('Próximo →')
        self._next_btn.setObjectName('primaryButton')
        self._next_btn.clicked.connect(self._next)
        nav_layout.addWidget(self._back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self._next_btn)
        layout.addWidget(nav)

    def _make_step0(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 16)
        logo = QLabel('🐙')
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet('font-size:72px;')
        title = QLabel('Bem-vindo ao Orbit')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size:24px;font-weight:700;')
        sub = QLabel('Seu hub de comunicação unificado\nTodos os seus apps em um só lugar.')
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet('color:#a6adc8;')
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(sub)
        return w

    def _make_step1(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 16)
        title = QLabel('Escolha o tema')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size:18px;font-weight:600;')
        layout.addWidget(title)
        cards_w = QWidget()
        cards_l = QHBoxLayout(cards_w)
        cards_l.setSpacing(16)
        self._theme_cards = {}
        for t, icon, label in [('dark', '🌙', 'Escuro'), ('light', '☀️', 'Claro'), ('system', '💻', 'Sistema')]:
            card = QFrame()
            card.setObjectName('themeCard')
            card.setFixedSize(120, 100)
            card.setCursor(Qt.PointingHandCursor)
            cl = QVBoxLayout(card)
            cl.setAlignment(Qt.AlignCenter)
            icon_lbl = QLabel(icon)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet('font-size:28px;')
            name_lbl = QLabel(label)
            name_lbl.setAlignment(Qt.AlignCenter)
            cl.addWidget(icon_lbl)
            cl.addWidget(name_lbl)
            card.mousePressEvent = lambda e, theme=t: self._select_theme(theme)
            self._theme_cards[t] = card
            cards_l.addWidget(card)
        layout.addWidget(cards_w)
        self._select_theme('dark')
        return w

    def _make_step2(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 16, 32, 8)
        layout.setSpacing(8)
        title = QLabel('Adicione seu primeiro serviço')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size:18px;font-weight:600;')
        sub = QLabel('Clique para selecionar (opcional)')
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet('color:#a6adc8;font-size:12px;')
        layout.addWidget(title)
        layout.addWidget(sub)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(12)
        services = [
            ('whatsapp', '💬', 'WhatsApp'),
            ('slack', '💼', 'Slack'),
            ('gmail', '📧', 'Gmail'),
            ('telegram', '✈️', 'Telegram'),
            ('discord', '🎮', 'Discord'),
            ('teams', '👥', 'Teams'),
        ]
        self._svc_cards = {}
        for i, (st, icon, name) in enumerate(services):
            card = QFrame()
            card.setObjectName('themeCard')
            card.setFixedSize(140, 60)
            card.setCursor(Qt.PointingHandCursor)
            cl = QHBoxLayout(card)
            cl.setSpacing(8)
            cl.addWidget(QLabel(icon))
            cl.addWidget(QLabel(name))
            card.mousePressEvent = lambda e, s=st: self._select_service(s)
            self._svc_cards[st] = card
            grid.addWidget(card, i // 3, i % 3)
        layout.addWidget(grid_w)
        skip = QPushButton('Pular este passo')
        skip.setFlat(True)
        skip.clicked.connect(self._next)
        layout.addWidget(skip, 0, Qt.AlignCenter)
        return w

    def _make_step3(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 16)
        logo = QLabel('🎉')
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet('font-size:56px;')
        title = QLabel('Tudo pronto!')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size:22px;font-weight:700;')
        checks = QLabel('✅ Tema configurado\n✅ Atalhos de teclado ativos\n✅ Notificações nativas\n✅ Hibernação automática')
        checks.setAlignment(Qt.AlignCenter)
        checks.setStyleSheet('line-height:1.8;color:#a6adc8;')
        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(checks)
        return w

    def _select_theme(self, theme: str):
        self._chosen_theme = theme
        for t, card in self._theme_cards.items():
            if t == theme:
                card.setStyleSheet('border:2px solid #cba6f7;border-radius:8px;')
            else:
                card.setStyleSheet('border:1px solid #45475a;border-radius:8px;')

    def _select_service(self, svc: str):
        self._chosen_service = svc
        for s, card in self._svc_cards.items():
            if s == svc:
                card.setStyleSheet('border:2px solid #cba6f7;border-radius:8px;')
            else:
                card.setStyleSheet('border:1px solid #45475a;border-radius:8px;')

    def _next(self):
        if self._step == 1:
            self.theme_chosen.emit(self._chosen_theme)
        if self._step == 3:
            if self._chosen_service:
                self.service_chosen.emit(self._chosen_service)
            self.accept()
            return
        self._step += 1
        self._stack.setCurrentIndex(self._step)
        self._back_btn.setVisible(self._step > 0)
        self._next_btn.setText('Concluir' if self._step == 3 else 'Próximo →')

    def _prev(self):
        if self._step > 0:
            self._step -= 1
            self._stack.setCurrentIndex(self._step)
            self._back_btn.setVisible(self._step > 0)
            self._next_btn.setText('Próximo →')

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .catalog import CATALOG, CatalogEntry, GOOGLE_TYPES, google_url
from .models import Account, Service, new_id, slugify


# ── catalog card (used inside AddServiceDialog) ────────────────────────────────

class _CatalogCard(QPushButton):  # pragma: no cover
    def __init__(self, entry: CatalogEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setFixedSize(96, 84)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName('catalogCard')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel(entry.icon)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(40, 40)
        icon.setStyleSheet(
            f'background:{entry.color}; border-radius:10px; color:rgba(255,255,255,0.92);'
            f'font-size:13px; font-weight:bold;'
        )
        layout.addWidget(icon)

        name = QLabel(entry.name)
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet('font-size:11px; color:#cdd6f4;')
        layout.addWidget(name)


# ── AddServiceDialog ───────────────────────────────────────────────────────────

class AddServiceDialog(QDialog):  # pragma: no cover
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Adicionar Serviço')
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self._selected_entry: Optional[CatalogEntry] = None
        self._service: Optional[Service] = None
        self._selected_color: str = '#6c7086'

        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_catalog_page())
        self._stack.addWidget(self._make_form_page())

        layout = QVBoxLayout(self)
        layout.addWidget(self._stack)

    def _make_catalog_page(self) -> QWidget:
        from .catalog import get_all_categories
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel('Escolha um serviço')
        title.setStyleSheet('font-size:15px; font-weight:bold; color:#cdd6f4; padding:16px 16px 8px;')
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 0, 12, 12)
        content_layout.setSpacing(4)

        self._cards: list[_CatalogCard] = []
        categories = get_all_categories()

        # Group entries by category preserving catalog order
        from collections import OrderedDict
        cat_entries: dict[str, list] = OrderedDict((c, []) for c in categories)
        for entry in CATALOG:
            cat = entry.category or 'Personalizado'
            if cat in cat_entries:
                cat_entries[cat].append(entry)

        # Separate 'Personalizado' to render last with a divider
        regular_cats = [(c, e) for c, e in cat_entries.items() if c != 'Personalizado' and e]
        custom_entries = cat_entries.get('Personalizado', [])

        for cat, entries in regular_cats:
            header = QLabel(cat.upper())
            header.setStyleSheet(
                'color:#6c7086; font-size:10px; font-weight:600;'
                ' letter-spacing:0.5px; padding:8px 4px 4px;'
            )
            content_layout.addWidget(header)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(8)

            for i, entry in enumerate(entries):
                card = _CatalogCard(entry)
                card.clicked.connect(lambda _, e=entry: self._on_entry_selected(e))
                grid.addWidget(card, i // 4, i % 4)
                self._cards.append(card)

            content_layout.addWidget(grid_widget)

        # Personalizado section — always last, with separator
        if custom_entries:
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet('color: #2e2e3d; margin: 8px 0;')
            content_layout.addWidget(sep)

            custom_header = QLabel('PERSONALIZADO')
            custom_header.setStyleSheet(
                'color:#cba6f7; font-size:10px; font-weight:700;'
                ' letter-spacing:0.8px; padding:4px 4px 4px;'
            )
            content_layout.addWidget(custom_header)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(8)

            for i, entry in enumerate(custom_entries):
                card = _CatalogCard(entry)
                card.clicked.connect(lambda _, e=entry: self._on_entry_selected(e))
                grid.addWidget(card, i // 4, i % 4)
                self._cards.append(card)

            content_layout.addWidget(grid_widget)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    def _make_form_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._form_title = QLabel()
        self._form_title.setStyleSheet('font-size:15px; font-weight:bold; color:#cdd6f4;')
        layout.addWidget(self._form_title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft)

        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText('ex: Trabalho, Pessoal')
        form.addRow('Nome / apelido', self._label_edit)

        self._url_edit = QLineEdit()
        form.addRow('URL', self._url_edit)

        layout.addLayout(form)

        # Custom service options (icon + color) — shown only for 'custom' type
        self._custom_container = QWidget()
        custom_layout = QVBoxLayout(self._custom_container)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(8)

        icon_form = QFormLayout()
        icon_form.setSpacing(8)
        self._icon_edit = QLineEdit()
        self._icon_edit.setMaxLength(2)
        self._icon_edit.setText('⚡')
        self._icon_edit.setPlaceholderText('2 letras ou emoji')
        icon_form.addRow('Ícone (2 letras/emoji)', self._icon_edit)
        custom_layout.addLayout(icon_form)

        color_label = QLabel('Cor do ícone')
        custom_layout.addWidget(color_label)

        _swatch_colors = [
            '#d46d2a', '#2e936d', '#2a8dc5', '#456ae6',
            '#b95d4b', '#6264a7', '#a259ff', '#ff5263',
            '#7b68ee', '#ff3d57', '#00ac47', '#6c7086',
        ]
        swatches_widget = QWidget()
        swatches_grid = QGridLayout(swatches_widget)
        swatches_grid.setContentsMargins(0, 0, 0, 0)
        swatches_grid.setSpacing(6)
        self._swatch_btns: list[QPushButton] = []
        for i, color in enumerate(_swatch_colors):
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setStyleSheet(
                f'background:{color}; border-radius:18px; border: 2px solid transparent;'
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, c=color: self._select_color(c))
            swatches_grid.addWidget(btn, i // 6, i % 6)
            self._swatch_btns.append(btn)
        custom_layout.addWidget(swatches_widget)

        self._custom_container.setVisible(False)
        layout.addWidget(self._custom_container)

        layout.addStretch()

        btns = QDialogButtonBox()
        self._back_btn = QPushButton('← Voltar')
        self._back_btn.setObjectName('secondaryButton')
        self._back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        btns.addButton(self._back_btn, QDialogButtonBox.ButtonRole.ResetRole)

        ok = btns.addButton('Adicionar', QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName('primaryButton')
        ok.clicked.connect(self._on_accept)

        layout.addWidget(btns)
        return page

    def _select_color(self, color: str):
        self._selected_color = color
        _swatch_colors = [
            '#d46d2a', '#2e936d', '#2a8dc5', '#456ae6',
            '#b95d4b', '#6264a7', '#a259ff', '#ff5263',
            '#7b68ee', '#ff3d57', '#00ac47', '#6c7086',
        ]
        for btn, c in zip(self._swatch_btns, _swatch_colors):
            border = '3px solid #ffffff' if c == color else '2px solid transparent'
            btn.setStyleSheet(f'background:{c}; border-radius:18px; border: {border};')

    def _on_entry_selected(self, entry: CatalogEntry):
        self._selected_entry = entry
        self._form_title.setText(f'Configurar — {entry.name}')
        self._label_edit.setText(entry.name)
        # For Google services, use the authuser=0 URL by default
        if entry.type in GOOGLE_TYPES:
            self._url_edit.setText(google_url(entry.type, 0))
        else:
            self._url_edit.setText(entry.default_url)
        self._custom_container.setVisible(entry.type == 'custom')
        if entry.type == 'custom':
            self._icon_edit.setText('⚡')
            self._selected_color = '#6c7086'
        self._stack.setCurrentIndex(1)
        self._label_edit.setFocus()
        self._label_edit.selectAll()

    def _on_accept(self):
        if not self._selected_entry:
            return
        label = self._label_edit.text().strip() or self._selected_entry.name
        url = self._url_edit.text().strip()
        if not url:
            return

        entry = self._selected_entry
        svc_id = new_id(entry.type)
        acc_id = new_id('acc')
        profile_name = f'{entry.type}-{slugify(label)}-{acc_id}'

        if entry.type == 'custom':
            icon = self._icon_edit.text()[:2] or '⚡'
            color = self._selected_color
        else:
            icon = entry.icon
            color = entry.color

        self._service = Service(
            id=svc_id,
            service_type=entry.type,
            name=label,
            icon=icon,
            color=color,
            accounts=[Account(id=acc_id, label=label, url=url,
                              profile_name=profile_name, authuser=0)],
        )
        self.accept()

    def get_service(self) -> Optional[Service]:
        return self._service


# ── AddAccountDialog ───────────────────────────────────────────────────────────

class AddAccountDialog(QDialog):  # pragma: no cover
    def __init__(self, service: Service, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Adicionar conta — {service.name}')
        self.setModal(True)
        self.setMinimumWidth(400)
        self._service = service
        self._account: Optional[Account] = None
        self._is_google = service.service_type in GOOGLE_TYPES

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f'Adicionar conta — {service.name}')
        title.setStyleSheet('font-size:15px; font-weight:bold; color:#cdd6f4;')
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText('ex: Trabalho, Pessoal')
        form.addRow('Nome da conta', self._label_edit)

        if self._is_google:
            # Authuser selector for Google services
            next_authuser = len(service.accounts)  # suggest next index
            self._authuser_spin = QSpinBox()
            self._authuser_spin.setRange(0, 9)
            self._authuser_spin.setValue(next_authuser)
            self._authuser_spin.setToolTip(
                '0 = primeira conta Google, 1 = segunda, 2 = terceira…\n'
                'Deve corresponder à ordem das contas no seu navegador.'
            )
            self._authuser_spin.valueChanged.connect(self._update_google_url)

            hint = QLabel('0 = 1ª conta  ·  1 = 2ª conta  ·  2 = 3ª conta…')
            hint.setStyleSheet('color:#6c7086; font-size:11px;')

            form.addRow('Conta Google (índice)', self._authuser_spin)
            form.addRow('', hint)

            self._url_edit = QLineEdit()
            self._url_edit.setText(google_url(service.service_type, next_authuser))
            self._url_edit.setReadOnly(True)
            self._url_edit.setStyleSheet('color:#6c7086;')
            form.addRow('URL gerada', self._url_edit)
        else:
            self._authuser_spin = None
            self._url_edit = QLineEdit()
            default_url = service.accounts[0].url if service.accounts else 'https://'
            self._url_edit.setText(default_url)
            form.addRow('URL', self._url_edit)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        btns.rejected.connect(self.reject)
        ok = btns.addButton('Adicionar', QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setObjectName('primaryButton')
        ok.clicked.connect(self._on_accept)
        layout.addWidget(btns)

        self._label_edit.setFocus()

    def _update_google_url(self, value: int):
        self._url_edit.setText(google_url(self._service.service_type, value))

    def _on_accept(self):
        label = self._label_edit.text().strip()
        url = self._url_edit.text().strip()
        if not label or not url:
            return
        acc_id = new_id('acc')
        profile_name = f'{self._service.service_type}-{slugify(label)}-{acc_id}'
        authuser = self._authuser_spin.value() if self._authuser_spin else 0
        self._account = Account(
            id=acc_id, label=label, url=url,
            profile_name=profile_name, authuser=authuser,
        )
        self.accept()

    def get_account(self) -> Optional[Account]:
        return self._account


# ── ConfigDialog ───────────────────────────────────────────────────────────────

class ConfigDialog(QDialog):  # pragma: no cover
    def __init__(self, service: Service, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Configurar — {service.name}')
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f'Configurar — {service.name}')
        title.setStyleSheet('font-size:15px; font-weight:bold; color:#cdd6f4;')
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit(service.name)
        form.addRow('Nome', self._name_edit)

        self._hibernate_combo = QComboBox()
        options = [('Nunca', None), ('5 min', 5), ('15 min', 15), ('30 min', 30), ('1 hora', 60)]
        for label, val in options:
            self._hibernate_combo.addItem(label, val)
        current = service.hibernate_after
        idx = next((i for i, (_, v) in enumerate(options) if v == current), 0)
        self._hibernate_combo.setCurrentIndex(idx)
        form.addRow('Hibernar após inatividade', self._hibernate_combo)

        # Notification sound row
        self._sound_path = service.notification_sound
        sound_widget = QWidget()
        sound_layout = QHBoxLayout(sound_widget)
        sound_layout.setContentsMargins(0, 0, 0, 0)
        sound_layout.setSpacing(4)

        self._sound_edit = QLineEdit()
        self._sound_edit.setReadOnly(True)
        self._sound_edit.setPlaceholderText('(padrão do sistema)')
        if self._sound_path:
            self._sound_edit.setText(os.path.basename(self._sound_path))
        sound_layout.addWidget(self._sound_edit, 1)

        browse_btn = QPushButton('Procurar...')
        browse_btn.setObjectName('secondaryButton')
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_sound)
        sound_layout.addWidget(browse_btn)

        test_btn = QPushButton('▶ Testar')
        test_btn.setObjectName('secondaryButton')
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.clicked.connect(self._test_sound)
        sound_layout.addWidget(test_btn)

        clear_btn = QPushButton('✕')
        clear_btn.setObjectName('secondaryButton')
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_sound)
        sound_layout.addWidget(clear_btn)

        form.addRow('Som de notificação', sound_widget)

        # ── Proxy row ──
        proxy_widget = QWidget()
        proxy_layout = QVBoxLayout(proxy_widget)
        proxy_layout.setContentsMargins(0, 0, 0, 0)
        proxy_layout.setSpacing(2)
        self._proxy_edit = QLineEdit()
        self._proxy_edit.setPlaceholderText('http://host:porta ou socks5://host:porta')
        self._proxy_edit.setText(service.proxy)
        proxy_hint = QLabel('Deixe vazio para usar conexão direta')
        proxy_hint.setStyleSheet('font-size:11px; color:#6c7086;')
        proxy_layout.addWidget(self._proxy_edit)
        proxy_layout.addWidget(proxy_hint)
        form.addRow('Proxy', proxy_widget)

        # ── Incognito row ──
        self._incognito_cb = QCheckBox('Modo incógnito (não salva sessão/cookies)')
        self._incognito_cb.setChecked(service.incognito)
        form.addRow('', self._incognito_cb)

        incognito_warn = QLabel('⚠ Sessão não será salva. Você precisará fazer login toda vez.')
        incognito_warn.setStyleSheet('font-size:11px; color:#fab387;')
        incognito_warn.setWordWrap(True)
        incognito_warn.setVisible(service.incognito)
        form.addRow('', incognito_warn)
        self._incognito_cb.toggled.connect(incognito_warn.setVisible)

        # ── Spellcheck row ──
        self._spellcheck_cb = QCheckBox('Habilitar verificação ortográfica (en-US, pt-BR)')
        self._spellcheck_cb.setChecked(getattr(service, 'spellcheck', True))
        form.addRow('', self._spellcheck_cb)

        # ── Tags row ──
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText('ex: trabalho, pessoal, produtividade')
        self._tags_edit.setText(', '.join(getattr(service, 'tags', [])))
        form.addRow('Tags', self._tags_edit)

        layout.addLayout(form)

        css_label = QLabel('CSS personalizado')
        layout.addWidget(css_label)

        self._css_edit = QPlainTextEdit()
        self._css_edit.setFixedHeight(120)
        self._css_edit.setPlaceholderText('/* ex: body { font-size: 15px !important; } */')
        self._css_edit.setPlainText(service.custom_css)
        layout.addWidget(self._css_edit)

        js_label = QLabel('JavaScript personalizado')
        layout.addWidget(js_label)
        self._js_edit = QPlainTextEdit()
        self._js_edit.setFixedHeight(100)
        self._js_edit.setPlaceholderText('// ex: document.body.style.fontSize = "16px";')
        self._js_edit.setPlainText(service.custom_js)
        layout.addWidget(self._js_edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName('primaryButton')
            ok_btn.setText('Salvar')
        layout.addWidget(btns)

        self._name_edit.setFocus()

    def _browse_sound(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Selecionar som de notificação', '', 'Áudio (*.wav *.mp3 *.ogg)'
        )
        if path:
            self._sound_path = path
            self._sound_edit.setText(os.path.basename(path))

    def _test_sound(self):
        if self._sound_path:
            from .sounds import play_sound
            play_sound(self._sound_path)

    def _clear_sound(self):
        self._sound_path = ''
        self._sound_edit.clear()

    def apply_to(self, service: Service) -> None:
        service.name = self._name_edit.text().strip() or service.name
        service.hibernate_after = self._hibernate_combo.currentData()
        service.custom_css = self._css_edit.toPlainText().strip()
        service.custom_js = self._js_edit.toPlainText().strip()
        service.notification_sound = self._sound_path
        service.proxy = self._proxy_edit.text().strip()
        service.incognito = self._incognito_cb.isChecked()
        service.spellcheck = self._spellcheck_cb.isChecked()
        raw_tags = self._tags_edit.text()
        service.tags = [t.strip() for t in raw_tags.split(',') if t.strip()]


# ── ConfirmDialog ──────────────────────────────────────────────────────────────

class ConfirmDialog(QDialog):  # pragma: no cover
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Confirmar')
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet('font-size:14px; color:#cdd6f4; line-height:1.6;')
        layout.addWidget(msg)

        btns = QDialogButtonBox()
        cancel = btns.addButton('Cancelar', QDialogButtonBox.ButtonRole.RejectRole)
        cancel.setObjectName('secondaryButton')
        cancel.clicked.connect(self.reject)

        remove = btns.addButton('Remover', QDialogButtonBox.ButtonRole.AcceptRole)
        remove.setObjectName('dangerButton')
        remove.clicked.connect(self.accept)

        layout.addWidget(btns)


class EditWorkspaceDialog(QDialog):  # pragma: no cover
    """Dialog for creating or editing a workspace (name + accent color)."""

    def __init__(self, name: str = '', accent: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle('Workspace')
        self.setModal(True)
        self.setMinimumWidth(360)
        self._accent = accent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit(name)
        self._name_edit.setPlaceholderText('Nome do workspace')
        form.addRow('Nome', self._name_edit)

        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(8)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 24)
        self._color_btn.setCursor(Qt.PointingHandCursor)
        self._color_btn.setToolTip('Escolher cor do workspace')
        self._color_btn.clicked.connect(self._pick_color)
        self._update_color_btn()

        self._color_label = QLabel(accent if accent else '(padrão)')
        self._color_label.setStyleSheet('color: #6c7086; font-size: 11px;')

        clear_btn = QPushButton('✕ Limpar')
        clear_btn.setObjectName('secondaryButton')
        clear_btn.setFixedHeight(24)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_color)

        color_layout.addWidget(self._color_btn)
        color_layout.addWidget(self._color_label)
        color_layout.addStretch()
        color_layout.addWidget(clear_btn)

        form.addRow('Cor do workspace', color_widget)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName('primaryButton')
            ok_btn.setText('Salvar')
        layout.addWidget(btns)

        self._name_edit.setFocus()

    def _pick_color(self):
        from PySide6.QtWidgets import QColorDialog
        current = QColor(self._accent) if self._accent else QColor('#7c6af7')
        color = QColorDialog.getColor(current, self, 'Escolher cor')
        if color.isValid():
            self._accent = color.name()
            self._update_color_btn()
            self._color_label.setText(self._accent)

    def _clear_color(self):
        self._accent = ''
        self._update_color_btn()
        self._color_label.setText('(padrão)')

    def _update_color_btn(self):
        if self._accent:
            self._color_btn.setStyleSheet(
                f'background: {self._accent}; border: 1px solid #444; border-radius: 4px;'
            )
        else:
            self._color_btn.setStyleSheet(
                'background: #2a2a3a; border: 1px solid #444; border-radius: 4px;'
            )

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def get_name(self) -> str:
        return self._name_edit.text().strip()

    def get_accent(self) -> str:
        return self._accent


class WorkspaceScheduleDialog(QDialog):  # pragma: no cover
    """Configure automatic workspace switching rules."""

    def __init__(self, workspaces, schedule, parent=None):
        super().__init__(parent)
        from .workspace_schedule import save_schedule
        self.setWindowTitle('Agendamento de Workspace')
        self.setMinimumSize(520, 400)
        self._workspaces = workspaces
        self._schedule = schedule
        self._save_fn = save_schedule

        lay = QVBoxLayout(self)

        self._enabled_cb = QCheckBox('Ativar troca automática de workspace por horário')
        self._enabled_cb.setChecked(schedule.enabled)
        lay.addWidget(self._enabled_cb)

        info = QLabel('Configure regras para trocar automaticamente o workspace conforme o horário do dia.')
        info.setWordWrap(True)
        info.setStyleSheet('color: #6c7086; font-size: 12px;')
        lay.addWidget(info)

        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self._rules_list = QListWidget()
        for rule in schedule.rules:
            ws_name = next((w.name for w in workspaces if w.id == rule.workspace_id), rule.workspace_id)
            days_str = ', '.join(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][d] for d in rule.days)
            label = (f"{ws_name}  |  {days_str}  |  "
                     f"{rule.start_hour:02d}:{rule.start_minute:02d} – "
                     f"{rule.end_hour:02d}:{rule.end_minute:02d}")
            item = QListWidgetItem(('✅ ' if rule.enabled else '❌ ') + label)
            item.setData(Qt.UserRole, rule)
            self._rules_list.addItem(item)
        lay.addWidget(self._rules_list)

        btns_row = QHBoxLayout()
        add_btn = QPushButton('+ Adicionar Regra')
        add_btn.clicked.connect(self._add_rule)
        del_btn = QPushButton('Remover')
        del_btn.clicked.connect(self._del_rule)
        btns_row.addWidget(add_btn)
        btns_row.addWidget(del_btn)
        btns_row.addStretch()
        lay.addLayout(btns_row)

        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._save)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def _add_rule(self):
        from .workspace_schedule import WorkspaceRule
        from PySide6.QtWidgets import QDialog, QListWidgetItem
        dlg = QDialog(self)
        dlg.setWindowTitle('Nova Regra')
        form = QFormLayout(dlg)
        ws_combo = QComboBox()
        for ws in self._workspaces:
            ws_combo.addItem(ws.name, ws.id)
        form.addRow('Workspace:', ws_combo)

        start_h = QSpinBox()
        start_h.setRange(0, 23)
        start_h.setValue(9)
        end_h = QSpinBox()
        end_h.setRange(0, 23)
        end_h.setValue(18)
        form.addRow('Hora início:', start_h)
        form.addRow('Hora fim:', end_h)

        day_checks = []
        days_row = QHBoxLayout()
        for i, d in enumerate(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']):
            cb = QCheckBox(d)
            cb.setChecked(i < 5)  # weekdays checked by default
            day_checks.append(cb)
            days_row.addWidget(cb)
        days_widget = QWidget()
        days_widget.setLayout(days_row)
        form.addRow('Dias:', days_widget)

        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(dlg.accept)
        box.rejected.connect(dlg.reject)
        form.addRow(box)

        if dlg.exec() == QDialog.Accepted:
            from .workspace_schedule import WorkspaceRule
            from PySide6.QtWidgets import QListWidgetItem
            rule = WorkspaceRule(
                workspace_id=ws_combo.currentData(),
                days=[i for i, cb in enumerate(day_checks) if cb.isChecked()],
                start_hour=start_h.value(),
                end_hour=end_h.value(),
            )
            self._schedule.rules.append(rule)
            ws_name = ws_combo.currentText()
            days_str = ', '.join(['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][d] for d in rule.days)
            label = f"{ws_name}  |  {days_str}  |  {rule.start_hour:02d}:00 – {rule.end_hour:02d}:00"
            item = QListWidgetItem('✅ ' + label)
            item.setData(Qt.UserRole, rule)
            self._rules_list.addItem(item)

    def _del_rule(self):
        row = self._rules_list.currentRow()
        if row >= 0:
            self._schedule.rules.pop(row)
            self._rules_list.takeItem(row)

    def _save(self):
        self._schedule.enabled = self._enabled_cb.isChecked()
        self._save_fn(self._schedule)
        self.accept()


# ── MasterPasswordDialog ──────────────────────────────────────────────────────

class MasterPasswordDialog(QDialog):  # pragma: no cover
    """Dialog to set or enter the master password for file encryption.

    mode='set'   — two fields (password + confirm) to create a new password.
    mode='enter' — single field to unlock with an existing password.
    """

    def __init__(self, mode: str = 'enter', parent=None):
        super().__init__(parent)
        self.setWindowTitle('🔐 Senha Mestre')
        self.setFixedWidth(360)
        self.setModal(True)
        self._mode = mode
        self._password = ''
        self._build_ui()

    @property
    def password(self) -> str:
        return self._password

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        if self._mode == 'set':
            title = QLabel('🔐 Definir Senha Mestre')
            hint = QLabel('A senha protege seus workspaces com AES-256-GCM.\nMínimo de 6 caracteres.')
        else:
            title = QLabel('🔐 Digite a Senha Mestre')
            hint = QLabel('Seus arquivos estão criptografados.\nDigite a senha para continuar.')

        title.setStyleSheet('font-size:15px; font-weight:bold; color:#cdd6f4;')
        hint.setWordWrap(True)
        hint.setStyleSheet('font-size:12px; color:#6c7086;')
        layout.addWidget(title)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)

        self._field = QLineEdit()
        self._field.setEchoMode(QLineEdit.EchoMode.Password)
        self._field.setPlaceholderText('Senha')
        form.addRow('Senha:', self._field)

        if self._mode == 'set':
            self._confirm = QLineEdit()
            self._confirm.setEchoMode(QLineEdit.EchoMode.Password)
            self._confirm.setPlaceholderText('Confirmar senha')
            form.addRow('Confirmar:', self._confirm)

            self._strength = QLabel('')
            self._strength.setStyleSheet('font-size:11px;')
            form.addRow('', self._strength)
            self._field.textChanged.connect(self._update_strength)

        layout.addLayout(form)

        self._error = QLabel('')
        self._error.setStyleSheet('color:#f38ba8; font-size:12px;')
        self._error.setWordWrap(True)
        layout.addWidget(self._error)

        if self._mode == 'enter':
            forgot = QLabel('<a href="#" style="color:#6c7086; font-size:11px;">Esqueci a senha</a>')
            forgot.setTextInteractionFlags(Qt.TextBrowserInteraction)
            forgot.linkActivated.connect(self._forgot_password)
            layout.addWidget(forgot)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText('Confirmar' if self._mode == 'set' else 'Desbloquear')
            ok_btn.setObjectName('primaryButton')
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._field.returnPressed.connect(self._accept)
        self._field.setFocus()

    def _update_strength(self, text: str):
        n = len(text)
        if n == 0:
            self._strength.setText('')
        elif n < 6:
            self._strength.setText('🔴 Muito curta')
            self._strength.setStyleSheet('font-size:11px; color:#f38ba8;')
        elif n < 10:
            self._strength.setText('🟡 Razoável')
            self._strength.setStyleSheet('font-size:11px; color:#f9e2af;')
        else:
            self._strength.setText('🟢 Forte')
            self._strength.setStyleSheet('font-size:11px; color:#a6e3a1;')

    def _accept(self):
        if self._mode == 'set':
            p1 = self._field.text()
            p2 = self._confirm.text()
            if len(p1) < 6:
                self._error.setText('A senha deve ter pelo menos 6 caracteres.')
                return
            if p1 != p2:
                self._error.setText('As senhas não correspondem.')
                return
            self._password = p1
        else:
            p = self._field.text()
            if not p:
                self._error.setText('Digite a senha.')
                return
            self._password = p
        self.accept()

    def _forgot_password(self):
        from PySide6.QtWidgets import QMessageBox
        result = QMessageBox.warning(
            self,
            'Esqueci a senha',
            'Sem a senha mestre, os arquivos criptografados não podem ser recuperados.\n\n'
            'Deseja apagar os dados criptografados e começar do zero?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._password = ''
            self.done(2)  # special code: caller should wipe encrypted data

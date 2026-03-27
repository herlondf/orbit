from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QFontMetrics
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
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
    QButtonGroup,
    QSizePolicy,
)

from .catalog import CATALOG, CatalogEntry, GOOGLE_TYPES, google_url
from .models import Account, Service, new_id, slugify
from .storage import load_settings, save_settings
from .theme import ACCENTS


# ── icon picker (used inside AddServiceDialog for custom services) ──────────────

_ICON_PALETTE = [
    # Symbols & tech
    '⚡', '🔥', '💡', '🚀', '🌟', '💎', '🔮', '🎯',
    '⭐', '🌈', '🌊', '🍀', '🦋', '🐝', '🦄', '🐉',
    # Communication
    '💬', '📧', '📞', '📱', '🔔', '📣', '📡', '🗨️',
    # Work & tools
    '💼', '📊', '📈', '🗂️', '📝', '✅', '🔒', '🔑',
    '🔍', '⚙️', '🛠️', '🖥️', '💾', '☁️', '🔗', '📦',
    # Media & arts
    '🎵', '🎮', '📺', '📸', '🎨', '🎬', '🎭', '📰',
    # Finance & shopping
    '💰', '🏦', '🛒', '💳', '📉', '🏷️', '🎁', '🏆',
    # Nature & places
    '🏠', '🏢', '🌍', '🗺️', '⛅', '🌙', '🌞', '🏔️',
]

_LETTER_ICONS = [
    'AI', 'WA', 'TG', 'SL', 'MS', 'GM', 'YT', 'FB',
    'IN', 'TW', 'RD', 'LI', 'GH', 'BB', 'SP', 'DC',
]


class _IconPickerWidget(QWidget):  # pragma: no cover
    """Visual emoji/letter icon picker for custom services."""

    icon_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = '⚡'
        self._icon_btns: list[QPushButton] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Preview + custom input row
        top = QHBoxLayout()
        top.setSpacing(10)

        self._preview = QLabel(self._current)
        self._preview.setFixedSize(44, 44)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet(
            'background:#313244; border-radius:10px; color:#cdd6f4;'
            'font-size:22px; border: 2px solid #45475a;'
        )
        top.addWidget(self._preview)

        self._custom_edit = QLineEdit()
        self._custom_edit.setMaxLength(3)
        self._custom_edit.setPlaceholderText('Texto ou emoji personalizado...')
        self._custom_edit.setStyleSheet(
            'background:#1e1e2e; border:1px solid #45475a; border-radius:8px;'
            'color:#cdd6f4; padding:4px 10px; font-size:13px;'
        )
        self._custom_edit.textChanged.connect(self._on_custom_text)
        top.addWidget(self._custom_edit, 1)
        root.addLayout(top)

        # Scrollable emoji grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setFixedHeight(164)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet('background:transparent;')

        grid_widget = QWidget()
        grid_widget.setStyleSheet('background:transparent;')
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 4, 0)
        grid.setSpacing(4)

        all_icons = _ICON_PALETTE + _LETTER_ICONS
        cols = 8
        for i, icon in enumerate(all_icons):
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                'QPushButton { background:#313244; border-radius:8px; font-size:16px;'
                '  border:2px solid transparent; color:#cdd6f4; }'
                'QPushButton:hover { background:#45475a; }'
                'QPushButton[selected="true"] { border-color:#89b4fa; background:#45475a; }'
            )
            btn.setProperty('selected', icon == self._current)
            btn.clicked.connect(lambda _, ic=icon, b=btn: self._select(ic, b))
            grid.addWidget(btn, i // cols, i % cols)
            self._icon_btns.append(btn)

        scroll.setWidget(grid_widget)
        root.addWidget(scroll)

    def _select(self, icon: str, btn: QPushButton):
        self._current = icon
        self._preview.setText(icon)
        self._custom_edit.blockSignals(True)
        self._custom_edit.clear()
        self._custom_edit.blockSignals(False)
        for b in self._icon_btns:
            b.setProperty('selected', b is btn)
            b.style().unpolish(b)
            b.style().polish(b)
        self.icon_changed.emit(icon)

    def _on_custom_text(self, text: str):
        if text:
            self._current = text[:2]
            self._preview.setText(self._current)
            for b in self._icon_btns:
                b.setProperty('selected', False)
                b.style().unpolish(b)
                b.style().polish(b)
            self.icon_changed.emit(self._current)

    def current_icon(self) -> str:
        return self._current

    def reset(self):
        self._current = '⚡'
        self._preview.setText('⚡')
        self._custom_edit.clear()
        for b in self._icon_btns:
            is_sel = b.text() == '⚡'
            b.setProperty('selected', is_sel)
            b.style().unpolish(b)
            b.style().polish(b)


# ── catalog card (used inside AddServiceDialog) ────────────────────────────────

_CATALOG_ROLE_ENTRY = Qt.UserRole


class _CatalogDelegate(QStyledItemDelegate):  # pragma: no cover
    """Paints catalog cards: colored icon box + name below. No QSS interference."""

    _CARD_W = 96
    _CARD_H = 88
    _ICON_SIZE = 40

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(self._CARD_W, self._CARD_H)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        entry: CatalogEntry = index.data(_CATALOG_ROLE_ENTRY)
        if entry is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)

        # Card background
        if is_selected:
            bg = QColor('#313244')
        elif is_hover:
            bg = QColor('#292942')
        else:
            bg = QColor('#1e1e2e')

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 8, 8)

        # Colored icon box (centered horizontally)
        icon_size = self._ICON_SIZE
        icon_x = rect.x() + (rect.width() - icon_size) // 2
        icon_y = rect.y() + 10
        icon_rect = QRect(icon_x, icon_y, icon_size, icon_size)

        # Try brand pixmap first (white fill on colored box)
        from .brand_icons import brand_icon, has_brand_icon
        px = brand_icon(entry.type, icon_size, '#FFFFFF') if has_brand_icon(entry.type) else None

        if px and not px.isNull():
            icon_color = QColor(entry.color) if entry.color else QColor('#6c7086')
            painter.setBrush(icon_color)
            painter.drawRoundedRect(icon_rect, 10, 10)
            scaled = px.scaled(icon_size - 10, icon_size - 10,
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
            px_x = icon_x + (icon_size - scaled.width()) // 2
            px_y = icon_y + (icon_size - scaled.height()) // 2
            painter.drawPixmap(px_x, px_y, scaled)
        else:
            icon_color = QColor(entry.color) if entry.color else QColor('#6c7086')
            painter.setBrush(icon_color)
            painter.drawRoundedRect(icon_rect, 10, 10)
            font = QFont()
            font.setPixelSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 230))
            painter.drawText(icon_rect, Qt.AlignCenter, entry.icon)

        # Name label (elided)
        name_y = icon_y + icon_size + 4
        name_rect = QRect(rect.x() + 4, name_y, rect.width() - 8, 20)
        name_font = QFont()
        name_font.setPixelSize(10)
        painter.setFont(name_font)
        painter.setPen(QColor('#cdd6f4'))
        fm = QFontMetrics(name_font)
        elided = fm.elidedText(entry.name, Qt.ElideRight, name_rect.width())
        painter.drawText(name_rect, Qt.AlignCenter | Qt.AlignTop, elided)

        # Selection border
        if is_selected:
            painter.setPen(QColor('#89b4fa'))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 8, 8)

        painter.restore()


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
        from .catalog import CATALOG
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header + search bar
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 8)
        header_layout.setSpacing(8)

        title = QLabel('Escolha um serviço')
        title.setStyleSheet('font-size:15px; font-weight:bold; color:#cdd6f4;')
        header_layout.addWidget(title)

        self._catalog_search = QLineEdit()
        self._catalog_search.setPlaceholderText('🔍  Buscar serviço...')
        self._catalog_search.setObjectName('catalogSearch')
        self._catalog_search.setStyleSheet(
            'QLineEdit#catalogSearch {'
            '  background:#1e1e2e; border:1px solid #313244; border-radius:8px;'
            '  color:#cdd6f4; padding:6px 12px; font-size:13px;'
            '}'
            'QLineEdit#catalogSearch:focus { border-color:#89b4fa; }'
        )
        self._catalog_search.textChanged.connect(self._filter_catalog)
        header_layout.addWidget(self._catalog_search)

        layout.addWidget(header_widget)

        # QListWidget in IconMode — no QSS interference on individual cells
        self._catalog_list = QListWidget()
        self._catalog_list.setFlow(QListWidget.Flow.LeftToRight)
        self._catalog_list.setWrapping(True)
        self._catalog_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._catalog_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._catalog_list.setSpacing(4)
        self._catalog_list.setUniformItemSizes(True)
        self._catalog_list.setItemDelegate(_CatalogDelegate())
        self._catalog_list.setStyleSheet(
            'QListWidget { background:#181825; border:none; padding:8px; }'
            'QListWidget::item { background:transparent; }'
        )
        self._catalog_list.itemClicked.connect(
            lambda item: self._on_entry_selected(item.data(_CATALOG_ROLE_ENTRY))
        )
        self._catalog_list.itemDoubleClicked.connect(
            lambda item: self._on_entry_selected(item.data(_CATALOG_ROLE_ENTRY))
        )

        # Populate — custom entries first
        custom = [e for e in CATALOG if (e.category or '') == 'Personalizado']
        regular = [e for e in CATALOG if (e.category or '') != 'Personalizado']

        for entry in custom + regular:
            item = QListWidgetItem()
            item.setData(_CATALOG_ROLE_ENTRY, entry)
            item.setToolTip(entry.name)
            item.setSizeHint(QSize(96, 88))
            self._catalog_list.addItem(item)

        layout.addWidget(self._catalog_list)
        return page

    def _filter_catalog(self, text: str):
        """Show/hide catalog items based on search text."""
        query = text.strip().lower()
        for i in range(self._catalog_list.count()):
            item = self._catalog_list.item(i)
            entry: CatalogEntry = item.data(_CATALOG_ROLE_ENTRY)
            visible = (
                not query
                or query in entry.name.lower()
                or query in (entry.category or '').lower()
            )
            item.setHidden(not visible)

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
        custom_layout.setSpacing(10)

        # Icon picker label
        icon_label = QLabel('Ícone')
        icon_label.setStyleSheet('font-size:12px; color:#a6adc8;')
        custom_layout.addWidget(icon_label)

        # Icon picker widget
        self._icon_picker = _IconPickerWidget()
        self._icon_picker.icon_changed.connect(self._on_icon_changed)
        custom_layout.addWidget(self._icon_picker)

        color_label = QLabel('Cor do ícone')
        color_label.setStyleSheet('font-size:12px; color:#a6adc8;')
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

    def _on_icon_changed(self, icon: str):
        pass  # icon_picker handles its own preview; no extra action needed

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
            self._icon_picker.reset()
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
            icon = self._icon_picker.current_icon() or '⚡'
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
    """Dialog for creating or editing a workspace (name only)."""

    def __init__(self, name: str = '', accent: str = '', bg_color: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle('Workspace')
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit(name)
        self._name_edit.setPlaceholderText('Nome do workspace')
        form.addRow('Nome', self._name_edit)
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

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def get_name(self) -> str:
        return self._name_edit.text().strip()

    def get_accent(self) -> str:
        return ''

    def get_bg_color(self) -> str:
        return ''


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


# ── General Settings Dialog ────────────────────────────────────────────────────

_NAV_BTN_STYLE = """
QPushButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {fg};
    font-size: 13px;
    text-align: left;
    padding: 8px 16px;
    min-height: 36px;
}}
QPushButton:hover {{ background: rgba(255,255,255,6); }}
QPushButton:checked {{ background: rgba(203,166,247,18); color: #cba6f7; font-weight: bold; }}
"""


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet('font-size:11px; font-weight:bold; color:#6c7086; letter-spacing:1px; margin-bottom:4px;')
    return lbl


def _separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet('color: #2e2e3d; margin: 8px 0;')
    return sep


class GeneralSettingsDialog(QDialog):  # pragma: no cover
    """Main application settings dialog — opened via Ctrl+, or gear button."""

    def __init__(self, callbacks: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configurações — Orbit')
        self.setModal(True)
        self.setMinimumSize(720, 520)
        self._cbs = callbacks or {}
        self._settings = load_settings()
        self._build_ui()

    # ── construction ──────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left nav panel
        nav = QWidget()
        nav.setObjectName('settingsNav')
        nav.setFixedWidth(190)
        nav.setStyleSheet(
            'QWidget#settingsNav { background: #16161a; border-right: 1px solid #2e2e3d; }'
        )
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(8, 20, 8, 16)
        nav_layout.setSpacing(2)

        title = QLabel('Configurações')
        title.setStyleSheet('font-size:14px; font-weight:bold; color:#cdd6f4; padding: 0 8px 14px;')
        nav_layout.addWidget(title)

        self._stack = QStackedWidget()
        pages = [
            ('Aparência',    self._page_appearance()),
            ('Barra Lateral',self._page_sidebar()),
            ('Comportamento',self._page_behavior()),
            ('Segurança',    self._page_security()),
            ('Privacidade',  self._page_privacy()),
            ('Atualizações', self._page_updates()),
            ('Sincronização',self._page_sync()),
        ]

        self._nav_btns: list[QPushButton] = []
        for i, (label, page) in enumerate(pages):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(_NAV_BTN_STYLE.format(fg='#a6adc8'))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._switch_page(idx))
            nav_layout.addWidget(btn)
            self._stack.addWidget(page)
            self._nav_btns.append(btn)

        nav_layout.addStretch()

        # Close button
        close_btn = QPushButton('Fechar')
        close_btn.setObjectName('primaryButton')
        close_btn.clicked.connect(self._save_and_close)
        nav_layout.addWidget(close_btn)

        root.addWidget(nav)
        root.addWidget(self._stack, 1)

        self._switch_page(0)

    def _switch_page(self, idx: int):
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)

    def _scroll_page(self, inner: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        return scroll

    # ── pages ─────────────────────────────────────────────────────────────────

    def _page_appearance(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(_section_title('TEMA'))

        self._theme_btns: dict[str, QPushButton] = {}
        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        cur_theme = self._settings.get('theme', 'dark')
        for t_id, t_label in [('dark', '🌙 Escuro'), ('light', '☀️ Claro'), ('system', '🖥️ Automático')]:
            btn = QPushButton(t_label)
            btn.setCheckable(True)
            btn.setChecked(cur_theme == t_id)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setObjectName('primaryButton' if cur_theme == t_id else '')
            btn.clicked.connect(lambda _, tid=t_id: self._select_theme(tid))
            theme_row.addWidget(btn)
            self._theme_btns[t_id] = btn
        lay.addLayout(theme_row)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('COR DE DESTAQUE'))

        self._accent_btns: dict[str, QPushButton] = {}
        accent_row = QHBoxLayout()
        accent_row.setSpacing(8)
        cur_accent = self._settings.get('accent', 'Iris')
        for name, color in ACCENTS.items():
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(cur_accent == name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            checked_style = f'QPushButton {{ background:{color}; color:#fff; border:2px solid {color}; border-radius:6px; }}'
            normal_style  = f'QPushButton {{ background:rgba(255,255,255,8); color:#cdd6f4; border:1px solid #3e3e52; border-radius:6px; }} QPushButton:hover {{ border-color:{color}; }}'
            btn.setStyleSheet(checked_style if cur_accent == name else normal_style)
            btn.clicked.connect(lambda _, n=name, c=color, ns=normal_style, cs=checked_style: self._select_accent(n, c, ns, cs))
            accent_row.addWidget(btn)
            self._accent_btns[name] = btn
        lay.addLayout(accent_row)

        lay.addStretch()
        return self._scroll_page(w)

    def _page_sidebar(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(_section_title('TAMANHO'))

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._compact_w_spin = QSpinBox()
        self._compact_w_spin.setRange(52, 120)
        self._compact_w_spin.setSuffix(' px')
        self._compact_w_spin.setValue(self._settings.get('sidebar_compact_width', 68))
        self._compact_w_spin.setToolTip('Largura da sidebar no modo minimizado')
        form.addRow('Largura minimizada:', self._compact_w_spin)

        self._expanded_w_spin = QSpinBox()
        self._expanded_w_spin.setRange(160, 400)
        self._expanded_w_spin.setSuffix(' px')
        self._expanded_w_spin.setValue(self._settings.get('sidebar_expanded_width', 220))
        self._expanded_w_spin.setToolTip('Largura da sidebar no modo expandido')
        form.addRow('Largura expandida:', self._expanded_w_spin)

        # Sidebar style picker
        self._sidebar_style_combo = QComboBox()
        _style_map = {
            'discord': 'Discord', 'arc': 'Arc Browser', 'dock': 'Dock (macOS)', 'notion': 'Notion',
            'slack': 'Slack', 'spotify': 'Spotify', 'teams': 'Teams',
            'telegram': 'Telegram', 'figma': 'Figma', 'linear': 'Linear',
        }
        for key, label in _style_map.items():
            self._sidebar_style_combo.addItem(label, key)
        current = self._settings.get('sidebar_style', 'discord')
        idx = list(_style_map.keys()).index(current) if current in _style_map else 0
        self._sidebar_style_combo.setCurrentIndex(idx)
        self._sidebar_style_combo.currentIndexChanged.connect(self._on_sidebar_style_changed)
        form.addRow('Estilo:', self._sidebar_style_combo)

        lay.addLayout(form)
        lay.addWidget(_separator())
        lay.addWidget(_section_title('COMPORTAMENTO'))

        # Position: left/right
        self._sidebar_pos_combo = QComboBox()
        self._sidebar_pos_combo.addItem('Esquerda', 'left')
        self._sidebar_pos_combo.addItem('Direita', 'right')
        cur_pos = self._settings.get('sidebar_position', 'left')
        self._sidebar_pos_combo.setCurrentIndex(0 if cur_pos == 'left' else 1)
        self._sidebar_pos_combo.currentIndexChanged.connect(self._on_sidebar_pos_changed)
        form.addRow('Posição:', self._sidebar_pos_combo)

        lay.addLayout(form)
        lay.addWidget(_separator())
        lay.addWidget(_section_title('APARÊNCIA'))

        # Opacity slider
        from PySide6.QtWidgets import QSlider
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel('Opacidade:'))
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(20, 100)
        self._opacity_slider.setValue(self._settings.get('sidebar_opacity', 100))
        self._opacity_slider.setTickInterval(10)
        self._opacity_lbl = QLabel(f'{self._opacity_slider.value()}%')
        self._opacity_lbl.setFixedWidth(36)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self._opacity_slider, 1)
        opacity_row.addWidget(self._opacity_lbl)
        lay.addLayout(opacity_row)

        # Color preset selector
        from PySide6.QtWidgets import QPushButton
        _COLOR_PRESETS = {
            'Padrão':     ('', ''),
            'Midnight':   ('#0d1117', '#1b2332'),
            'Ocean':      ('#0a1628', '#0d3b66'),
            'Forest':     ('#0d1a0d', '#1a3a1a'),
            'Wine':       ('#1a0d14', '#3d1a2a'),
            'Slate':      ('#1e2028', '#2d3040'),
            'Charcoal':   ('#111111', '#222222'),
            'Navy':       ('#0a0e1a', '#1a2040'),
            'Obsidian':   ('#080808', '#1a1a1a'),
        }
        lay.addWidget(QLabel('Preset de cores:'))
        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        cur_bg = self._settings.get('sidebar_custom_bg', '')
        col = 0
        for name, (bg, border) in _COLOR_PRESETS.items():
            btn = QPushButton(name)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            is_active = (cur_bg == bg)
            preview_bg = bg or '#1c1c23'
            if is_active:
                btn.setStyleSheet(f'background:{preview_bg}; color:#fff; border:2px solid {self._settings.get("accent", "#7c6af7")}; border-radius:6px; font-size:10px;')
            else:
                btn.setStyleSheet(f'background:{preview_bg}; color:#aaa; border:1px solid #3e3e52; border-radius:6px; font-size:10px;')
            btn.clicked.connect(lambda _, b=bg, br=border, n=name: self._apply_color_preset(b, br, n))
            preset_grid.addWidget(btn, col // 3, col % 3)
            col += 1
        lay.addLayout(preset_grid)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('COMPORTAMENTO'))

        self._starts_compact_chk = QCheckBox('Iniciar com a barra lateral minimizada')
        self._starts_compact_chk.setChecked(self._settings.get('sidebar_compact', True))
        lay.addWidget(self._starts_compact_chk)

        lay.addStretch()
        return self._scroll_page(w)

    def _page_behavior(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(_section_title('BANDEJA DO SISTEMA'))

        self._show_tray_chk = QCheckBox('Mostrar ícone na bandeja do sistema')
        self._show_tray_chk.setChecked(self._settings.get('show_tray', True))
        lay.addWidget(self._show_tray_chk)

        self._minimize_tray_chk = QCheckBox('Minimizar para a bandeja ao fechar a janela')
        self._minimize_tray_chk.setChecked(self._settings.get('minimize_to_tray', False))
        lay.addWidget(self._minimize_tray_chk)

        # Force show_tray if minimize_to_tray is on
        self._minimize_tray_chk.toggled.connect(
            lambda on: self._show_tray_chk.setChecked(True) if on else None
        )

        note = QLabel('Se "Minimizar para bandeja" estiver ativo, o ícone da bandeja ficará sempre visível.')
        note.setWordWrap(True)
        note.setStyleSheet('color:#6c7086; font-size:11px;')
        lay.addWidget(note)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('INICIALIZAÇÃO'))

        self._startup_chk = QCheckBox('Iniciar automaticamente com o Windows')
        startup_cb = self._cbs.get('is_startup_enabled')
        self._startup_chk.setChecked(startup_cb() if callable(startup_cb) else False)
        self._startup_chk.toggled.connect(self._on_startup_toggled)
        lay.addWidget(self._startup_chk)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('SERVIÇOS'))

        self._ws_enabled_chk = QCheckBox('Habilitar seletor de workspaces na barra lateral')
        self._ws_enabled_chk.setChecked(self._settings.get('workspaces_enabled', True))
        lay.addWidget(self._ws_enabled_chk)

        self._preload_chk = QCheckBox('Pré-carregar todos os serviços na abertura')
        self._preload_chk.setChecked(self._settings.get('preload_on_start', False))
        preload_note = QLabel('Carrega os serviços em segundo plano ao iniciar. '
                              'Consome mais memória, mas elimina o delay ao trocar de serviço.')
        preload_note.setWordWrap(True)
        preload_note.setStyleSheet('color:#6c7086; font-size:11px;')
        lay.addWidget(self._preload_chk)
        lay.addWidget(preload_note)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('NOTIFICAÇÕES'))

        notif_row = QHBoxLayout()
        notif_row.setSpacing(10)
        notif_lbl = QLabel('Estilo de notificação:')
        notif_lbl.setStyleSheet('font-size:13px;')
        self._notif_style_combo = QComboBox()
        self._notif_style_combo.addItem('Orbit (toast interno)', 'orbit')
        self._notif_style_combo.addItem('Sistema (bandeja do Windows)', 'system')
        self._notif_style_combo.addItem('Ambos', 'both')
        cur = self._settings.get('notification_style', 'orbit')
        idx = self._notif_style_combo.findData(cur)
        self._notif_style_combo.setCurrentIndex(max(0, idx))
        notif_row.addWidget(notif_lbl)
        notif_row.addWidget(self._notif_style_combo)
        notif_row.addStretch()
        lay.addLayout(notif_row)

        notif_note = QLabel(
            '<b>Orbit:</b> toast animado dentro do app. '
            '<b>Sistema:</b> notificação nativa do Windows via bandeja. '
            '<b>Ambos:</b> exibe os dois (pode gerar duplicatas em alguns serviços).'
        )
        notif_note.setWordWrap(True)
        notif_note.setStyleSheet('color:#6c7086; font-size:11px;')
        lay.addWidget(notif_note)

        lay.addStretch()
        return self._scroll_page(w)

    def _page_security(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(_section_title('BLOQUEIO POR PIN'))
        pin_desc = QLabel('Configure um PIN de 4 a 8 dígitos para bloquear o Orbit automaticamente após inatividade.')
        pin_desc.setWordWrap(True)
        pin_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(pin_desc)
        pin_btn = QPushButton('Configurar PIN...')
        pin_btn.setObjectName('primaryButton')
        pin_btn.setFixedWidth(200)
        pin_btn.clicked.connect(self._on_pin_clicked)
        lay.addWidget(pin_btn)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('CRIPTOGRAFIA'))
        enc_desc = QLabel('Proteja seus workspaces e configurações com criptografia AES-256-GCM usando uma senha mestre.')
        enc_desc.setWordWrap(True)
        enc_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(enc_desc)
        enc_btn = QPushButton('Criptografar arquivos...')
        enc_btn.setFixedWidth(200)
        enc_btn.clicked.connect(self._on_encrypt_clicked)
        lay.addWidget(enc_btn)

        lay.addStretch()
        return self._scroll_page(w)

    def _page_privacy(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(_section_title('BLOQUEADOR DE ANÚNCIOS'))
        ad_desc = QLabel('Bloqueia scripts de rastreamento e anúncios em todos os serviços abertos no Orbit.')
        ad_desc.setWordWrap(True)
        ad_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(ad_desc)

        self._ad_block_chk = QCheckBox('Ativar bloqueador de anúncios')
        self._ad_block_chk.setChecked(self._settings.get('ad_block', True))
        lay.addWidget(self._ad_block_chk)

        lay.addStretch()
        return self._scroll_page(w)

    def _page_updates(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(_section_title('ATUALIZAÇÕES'))
        upd_desc = QLabel('O Orbit verifica automaticamente atualizações ao iniciar. Você também pode verificar manualmente.')
        upd_desc.setWordWrap(True)
        upd_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(upd_desc)

        upd_btn = QPushButton('Verificar atualizações agora')
        upd_btn.setObjectName('primaryButton')
        upd_btn.setFixedWidth(240)
        upd_btn.clicked.connect(self._on_check_updates)
        lay.addWidget(upd_btn)

        lay.addStretch()
        return self._scroll_page(w)

    def _page_sync(self) -> QScrollArea:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(20)

        lay.addWidget(_section_title('SINCRONIZAÇÃO NA NUVEM'))
        gist_desc = QLabel('Sincronize suas configurações via GitHub Gist para manter múltiplos dispositivos atualizados.')
        gist_desc.setWordWrap(True)
        gist_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(gist_desc)
        gist_btn = QPushButton('Configurar GitHub Gist...')
        gist_btn.setObjectName('primaryButton')
        gist_btn.setFixedWidth(240)
        gist_btn.clicked.connect(self._on_gist_sync)
        lay.addWidget(gist_btn)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('WEBDAV / ONEDRIVE'))
        webdav_desc = QLabel('Sincronize com qualquer servidor WebDAV, incluindo OneDrive, Nextcloud e outros.')
        webdav_desc.setWordWrap(True)
        webdav_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(webdav_desc)
        webdav_btn = QPushButton('Configurar WebDAV / OneDrive...')
        webdav_btn.setFixedWidth(240)
        webdav_btn.clicked.connect(self._on_webdav)
        lay.addWidget(webdav_btn)

        lay.addWidget(_separator())
        lay.addWidget(_section_title('MIGRAÇÃO'))
        import_desc = QLabel('Importe serviços e configurações de aplicativos como Rambox ou Ferdium.')
        import_desc.setWordWrap(True)
        import_desc.setStyleSheet('color:#a6adc8; font-size:12px;')
        lay.addWidget(import_desc)
        import_btn = QPushButton('Importar do Rambox/Ferdium...')
        import_btn.setFixedWidth(240)
        import_btn.clicked.connect(self._on_import)
        lay.addWidget(import_btn)

        lay.addStretch()
        return self._scroll_page(w)

    # ── actions ───────────────────────────────────────────────────────────────

    def _select_theme(self, theme_id: str):
        self._settings['theme'] = theme_id
        for tid, btn in self._theme_btns.items():
            btn.setChecked(tid == theme_id)
            btn.setObjectName('primaryButton' if tid == theme_id else '')
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        cb = self._cbs.get('apply_theme')
        if callable(cb):
            cb(theme_id)

    def _select_accent(self, name: str, color: str, normal_style: str, checked_style: str):
        self._settings['accent'] = name
        for n, btn in self._accent_btns.items():
            cur_c = ACCENTS[n]
            cur_ns = f'QPushButton {{ background:rgba(255,255,255,8); color:#cdd6f4; border:1px solid #3e3e52; border-radius:6px; }} QPushButton:hover {{ border-color:{cur_c}; }}'
            cur_cs = f'QPushButton {{ background:{cur_c}; color:#fff; border:2px solid {cur_c}; border-radius:6px; }}'
            btn.setChecked(n == name)
            btn.setStyleSheet(cur_cs if n == name else cur_ns)
        cb = self._cbs.get('set_accent')
        if callable(cb):
            cb(name)

    def _on_startup_toggled(self, checked: bool):
        cb = self._cbs.get('set_startup')
        if callable(cb):
            cb(checked)

    def _on_pin_clicked(self):
        cb = self._cbs.get('show_pin_config')
        if callable(cb):
            cb()

    def _on_encrypt_clicked(self):
        cb = self._cbs.get('show_encrypt_config')
        if callable(cb):
            cb()

    def _on_check_updates(self):
        cb = self._cbs.get('check_updates')
        if callable(cb):
            cb()

    def _on_gist_sync(self):
        cb = self._cbs.get('show_cloud_sync')
        if callable(cb):
            cb()

    def _on_webdav(self):
        cb = self._cbs.get('show_webdav')
        if callable(cb):
            cb()

    def _on_import(self):
        cb = self._cbs.get('show_import')
        if callable(cb):
            cb()

    def _on_sidebar_style_changed(self, index):
        style = self._sidebar_style_combo.currentData()
        cb = self._cbs.get('apply_sidebar_style')
        if callable(cb):
            cb(style)

    def _on_sidebar_pos_changed(self, index):
        pos = self._sidebar_pos_combo.currentData()
        cb = self._cbs.get('apply_sidebar_position')
        if callable(cb):
            cb(pos)

    def _on_opacity_changed(self, value):
        self._opacity_lbl.setText(f'{value}%')
        cb = self._cbs.get('apply_sidebar_opacity')
        if callable(cb):
            cb(value)

    def _apply_color_preset(self, bg: str, border: str, name: str):
        cb_bg = self._cbs.get('apply_sidebar_custom_bg')
        cb_border = self._cbs.get('apply_sidebar_custom_border')
        if callable(cb_bg):
            cb_bg(bg)
        if callable(cb_border):
            cb_border(border)

    # ── save & close ──────────────────────────────────────────────────────────

    def _save_and_close(self):
        # Sidebar sizes
        self._settings['sidebar_compact_width']  = self._compact_w_spin.value()
        self._settings['sidebar_expanded_width'] = self._expanded_w_spin.value()
        self._settings['sidebar_compact'] = self._starts_compact_chk.isChecked()
        self._settings['sidebar_style'] = self._sidebar_style_combo.currentData()
        self._settings['sidebar_position'] = self._sidebar_pos_combo.currentData()
        self._settings['sidebar_opacity'] = self._opacity_slider.value()

        # Behavior / tray
        min_tray = self._minimize_tray_chk.isChecked()
        show_tray = self._show_tray_chk.isChecked()
        if min_tray:
            show_tray = True  # enforce dependency
        self._settings['minimize_to_tray'] = min_tray
        self._settings['show_tray'] = show_tray

        # Privacy / ad block
        ad_block = self._ad_block_chk.isChecked()
        self._settings['ad_block'] = ad_block
        cb = self._cbs.get('set_ad_block')
        if callable(cb):
            cb(ad_block)

        # Services — workspace toggle + preload
        ws_enabled = self._ws_enabled_chk.isChecked()
        self._settings['workspaces_enabled'] = ws_enabled
        cb = self._cbs.get('apply_workspace_enabled')
        if callable(cb):
            cb(ws_enabled)

        preload = self._preload_chk.isChecked()
        self._settings['preload_on_start'] = preload

        # Notifications
        self._settings['notification_style'] = self._notif_style_combo.currentData()

        save_settings(self._settings)

        # Notify parent to apply sidebar width changes
        cb = self._cbs.get('apply_sidebar_widths')
        if callable(cb):
            cb(
                self._settings['sidebar_compact_width'],
                self._settings['sidebar_expanded_width'],
            )

        # Apply tray visibility
        cb = self._cbs.get('apply_tray_settings')
        if callable(cb):
            cb(show_tray)

        self.accept()

    def closeEvent(self, event):
        self._save_and_close()


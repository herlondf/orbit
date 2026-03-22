from __future__ import annotations

import os
import time
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QSize, QEvent, QRect, QUrl, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QBrush,
    QColor,
    QContextMenuEvent,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .dialogs import (
    AddAccountDialog,
    AddServiceDialog,
    ConfigDialog,
    ConfirmDialog,
    EditWorkspaceDialog,
    MasterPasswordDialog,
)
from .encryption import (
    clear_session_password,
    encrypt_file,
    get_session_password,
    hash_password,
    is_encrypted,
    set_session_password,
    verify_password_hash,
)
from .models import Account, Service, ServiceGroup, Workspace
from .storage import load_services, save_services, load_settings, save_settings, load_workspaces, save_workspaces, load_shortcuts, save_shortcuts
from .theme import get_tokens, ACCENTS, ThemeMode
from . import gist_sync as _gist_sync
from .importer import import_rambox, import_ferdium
from .webview import ServiceView, _GOOGLE_TYPES, set_ad_block
from .cookie_bridge import import_google_cookies, is_browser_running, find_browser
from .stats import record_session, get_weekly_totals, fmt_duration
from .icons import IconFetcher, get_cached_pixmap, icon as svg_icon
from .sounds import play_sound
from .notif_history import load_history, add_notification, get_history, clear_history
from .quiet_hours import is_quiet_now
from .dashboard import DashboardWidget
from .lock_screen import LockScreen, hash_pin
from .onboarding import OnboardingDialog
from .hover_effect import apply_hover_effect
from .toast import ToastManager

# ── Theme system (delegates to app/theme.py) ─────────────────────────────────
# ── Custom sidebar button ──────────────────────────────────────────────────────

class ServiceButton(QPushButton):
    """
    Sidebar button: coloured icon square + unread badge + active ring.
    Drawn entirely in paintEvent to avoid layout complexity.
    """

    hovered = Signal(bool)

    def __init__(self, service: Service, compact: bool = True, parent=None):
        super().__init__(parent)
        self.service = service
        self._compact = compact
        self._pixmap: Optional[QPixmap] = None
        if compact:
            self.setFixedSize(52, 52)
        else:
            self.setFixedHeight(52)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._badge = service.unread
        self._hovered = False
        self._status: str = 'idle'
        self._pulse_scale = 1.0
        self.setAttribute(Qt.WA_Hover)
        self.setProperty('active', False)

    def set_active(self, active: bool):
        self.setProperty('active', active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_badge(self, count: int):
        self._badge = count
        self.update()

    def set_status(self, status: str):
        self._status = status
        self.update()

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def pulse_badge(self):
        """Trigger a brief scale pulse on the badge to attract attention."""
        self._pulse_scale = 1.4
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(50)
        step = [0]
        def _tick():
            step[0] += 1
            self._pulse_scale = max(1.0, 1.4 - step[0] * 0.08)
            self.update()
            if step[0] >= 5:
                self._pulse_timer.stop()
                self._pulse_scale = 1.0
                self.update()
        self._pulse_timer.timeout.connect(_tick)
        self._pulse_timer.start()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        self.hovered.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        self.hovered.emit(False)
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        icon_size = 36
        ix = (w - icon_size) // 2 if self._compact else 12
        iy = max((h - icon_size) // 2, 8)

        # Active indicator: left accent bar + subtle background
        if self.isChecked():
            p.setBrush(QBrush(QColor('#cba6f7')))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 8, 3, h - 16, 2, 2)
            p.setBrush(QBrush(QColor(203, 166, 247, 30)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(4, 2, w - 8, h - 4, 8, 8)
        elif self._hovered:
            p.setBrush(QBrush(QColor(255, 255, 255, 12)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(4, 2, w - 8, h - 4, 8, 8)

        # Icon background
        p.setBrush(QBrush(QColor(self.service.color)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(ix, iy, icon_size, icon_size, 9, 9)

        # Icon: pixmap or text
        if self._pixmap and not self._pixmap.isNull():
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            scaled = self._pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            px_x = ix + (icon_size - scaled.width()) // 2
            px_y = iy + (icon_size - scaled.height()) // 2
            p.drawPixmap(px_x, px_y, scaled)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 230)))
            font = QFont('Segoe UI', 11, QFont.Bold)
            p.setFont(font)
            p.drawText(ix, iy, icon_size, icon_size, Qt.AlignCenter, self.service.icon)

        # Service name label in normal (non-compact) mode
        if not self._compact:
            text_x = ix + icon_size + 10
            avail_w = w - text_x - 12
            p.setPen(QPen(QColor('#cdd6f4')))
            font = QFont('Inter', 10, QFont.Medium)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 0.2)
            p.setFont(font)
            fm = p.fontMetrics()
            elided = fm.elidedText(self.service.name, Qt.ElideRight, avail_w)
            p.drawText(text_x, 0, avail_w, h, Qt.AlignVCenter | Qt.AlignLeft, elided)

        # Badge
        if self._badge > 0:
            badge_text = str(self._badge) if self._badge <= 99 else '99+'
            badge_w = max(18, len(badge_text) * 7 + 6)
            badge_h = 16
            if self._compact:
                bx = ix + icon_size - badge_w // 2
                by = iy - 6
            else:
                bx = ix + icon_size - badge_w + 6
                by = iy - 4
            pulse = getattr(self, '_pulse_scale', 1.0)
            if pulse != 1.0:
                cx = bx + badge_w / 2
                cy = by + badge_h / 2
                p.save()
                p.translate(cx, cy)
                p.scale(pulse, pulse)
                p.translate(-cx, -cy)
            p.setBrush(QBrush(QColor('#f38ba8')))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(bx, by, badge_w, badge_h, 8, 8)
            p.setPen(QPen(QColor('#1e1e2e')))
            p.setFont(QFont('Segoe UI', 8, QFont.Bold))
            p.drawText(bx, by, badge_w, badge_h, Qt.AlignCenter, badge_text)
            if pulse != 1.0:
                p.restore()

        # Status dot
        _status_colors = {
            'loading': '#fab387',
            'ready': '#a6e3a1',
            'error': '#f38ba8',
        }
        dot_color = _status_colors.get(self._status)
        if dot_color:
            dot_x = ix + icon_size - 8
            dot_y = iy + icon_size - 8
            p.setBrush(QBrush(QColor('#ffffff')))
            p.setPen(Qt.NoPen)
            p.drawEllipse(dot_x - 1, dot_y - 1, 10, 10)
            p.setBrush(QBrush(QColor(dot_color)))
            p.drawEllipse(dot_x, dot_y, 8, 8)

        # Incognito badge (🕵 in top-left corner of icon)
        if getattr(self.service, 'incognito', False):
            p.setPen(QPen(QColor('#cdd6f4')))
            p.setFont(QFont('Segoe UI Emoji', 9))
            p.drawText(ix - 2, iy - 2, 14, 14, Qt.AlignCenter, '🕵')

    def contextMenuEvent(self, event: QContextMenuEvent):
        # Propagate to window via signal (globalPosition().toPoint() is Qt6 API)
        self._ctx_pos = event.globalPosition().toPoint()
        self.customContextMenuRequested.emit(event.pos())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, '_drag_start'):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return
        from PySide6.QtGui import QDrag
        from PySide6.QtCore import QMimeData, QByteArray
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData('application/x-orbit-service', QByteArray(self.service.id.encode()))
        drag.setMimeData(mime)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self._drag_start)
        drag.exec(Qt.MoveAction)


# ── Small inline icon label (header) ──────────────────────────────────────────

class _IconLabel(QWidget):
    def __init__(self, service: Service, size: int = 24, parent=None):
        super().__init__(parent)
        self._service = service
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        radius = self._size * 0.25
        p.setBrush(QBrush(QColor(self._service.color)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, self._size, self._size, radius, radius)
        p.setPen(QPen(QColor(255, 255, 255, 230)))
        font_size = max(8, self._size // 3)
        p.setFont(QFont('Segoe UI', font_size, QFont.Bold))
        p.drawText(0, 0, self._size, self._size, Qt.AlignCenter, self._service.icon)


# ── Rich tooltip popup ────────────────────────────────────────────────────────

class _RichTooltip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(3)
        self._name_lbl = QLabel()
        self._name_lbl.setStyleSheet('font-weight:bold; font-size:13px; color:#cdd6f4;')
        self._badge_lbl = QLabel()
        self._badge_lbl.setStyleSheet('font-size:11px; color:#f38ba8;')
        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet('font-size:11px; color:#a6adc8;')
        self._layout.addWidget(self._name_lbl)
        self._layout.addWidget(self._badge_lbl)
        self._layout.addWidget(self._status_lbl)
        self.setStyleSheet('background:#313244; border-radius:8px; border:1px solid #45475a;')

    def show_for(self, service, btn_global_rect):
        from PySide6.QtCore import QRect, QPoint
        self._name_lbl.setText(service.name)
        if service.unread > 0:
            self._badge_lbl.setText(f'🔴 {service.unread} não lida(s)')
            self._badge_lbl.show()
        else:
            self._badge_lbl.hide()
        accounts_text = ', '.join(a.label for a in service.accounts) if service.accounts else 'Nenhuma conta'
        self._status_lbl.setText(f'👤 {accounts_text}')
        self.adjustSize()
        # btn_global_rect may be QRect or QPoint
        if isinstance(btn_global_rect, QRect):
            x = btn_global_rect.right() + 8
            y = btn_global_rect.top() + (btn_global_rect.height() - self.height()) // 2
        else:  # QPoint
            x = btn_global_rect.x() + 8
            y = btn_global_rect.y() - self.height() // 2
        self.move(x, y)
        self.show()


# ── Connection status badge (header) ──────────────────────────────────────────

class _StatusBadge(QWidget):
    """Small colored badge showing connection status: connecting / ready / error."""

    COLORS = {
        'connecting': '#d4a843',
        'ready':      '#52a97f',
        'error':      '#e8735a',
        'idle':       '#3e3e52',
    }
    LABELS = {
        'connecting': 'Conectando...',
        'ready':      'Conectado',
        'error':      'Erro',
        'idle':       '',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = 'idle'
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(5)

        self._dot = QWidget()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet('border-radius: 4px; background-color: #3e3e52;')
        layout.addWidget(self._dot)

        self._label = QLabel('')
        self._label.setStyleSheet('font-size: 11px; color: #6e6e8a; background: transparent;')
        layout.addWidget(self._label)

        self.setVisible(False)

    def set_status(self, status: str):
        self._status = status
        color = self.COLORS.get(status, '#3e3e52')
        label = self.LABELS.get(status, '')
        self._dot.setStyleSheet(f'border-radius: 4px; background-color: {color};')
        self._label.setText(label)
        self._label.setStyleSheet(f'font-size: 11px; color: {color}; background: transparent;')
        self.setVisible(status != 'idle')


# ── Glass sidebar ─────────────────────────────────────────────────────────────

class _GlassSidebar(QWidget):
    """Sidebar widget with a glassmorphism-style painted background."""

    def __init__(self, accent_color: str = '#7c6af7', parent=None):
        super().__init__(parent)
        self._accent = accent_color
        self.setObjectName('sidebar')
        # Override the global QSS background so our paintEvent shows through
        self.setStyleSheet('QWidget#sidebar { background: transparent; border-right: none; }')

    def set_accent(self, color: str):
        self._accent = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Base gradient — top-to-bottom dark
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(26, 26, 36, 252))
        grad.setColorAt(1, QColor(18, 18, 26, 255))
        p.fillRect(0, 0, w, h, grad)

        # Accent top glow strip (2px, fades left→right)
        ac = QColor(self._accent)
        ac.setAlpha(60)
        ac2 = QColor(self._accent)
        ac2.setAlpha(0)
        top_grad = QLinearGradient(0, 0, w, 0)
        top_grad.setColorAt(0, ac)
        top_grad.setColorAt(1, ac2)
        p.fillRect(0, 0, w, 2, top_grad)

        # Right-edge border
        p.setPen(QColor(50, 50, 65, 200))
        p.drawLine(w - 1, 0, w - 1, h)

        # Subtle horizontal scan lines every 40px
        p.setPen(QColor(255, 255, 255, 8))
        for y in range(0, h, 40):
            p.drawLine(0, y, w, y)

        super().paintEvent(event)


# ── Privacy overlay ────────────────────────────────────────────────────────────

class _PrivacyOverlay(QWidget):
    """Full-screen privacy overlay — hides web content when privacy mode is on."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('privacyOverlay')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.fillRect(self.rect(), QColor(15, 15, 20, 235))

        cx = self.width() // 2
        cy = self.height() // 2

        # Lock icon
        p.setPen(QColor(220, 220, 230))
        font = p.font()
        font.setPointSize(32)
        p.setFont(font)
        p.drawText(cx - 20, cy - 30, '🔒')

        # Main message
        font.setPointSize(14)
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        p.setPen(QColor(160, 160, 180))
        p.drawText(
            QRect(0, cy + 10, self.width(), 40),
            Qt.AlignmentFlag.AlignHCenter,
            'Orbit — Conteúdo protegido',
        )

        # Hint
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Normal)
        p.setFont(font)
        p.setPen(QColor(100, 100, 120))
        p.drawText(
            QRect(0, cy + 50, self.width(), 30),
            Qt.AlignmentFlag.AlignHCenter,
            'Pressione Ctrl+Shift+P para desativar',
        )


# ── Main window ────────────────────────────────────────────────────────────────

class OrbitWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        load_history()
        self._init_encryption()
        self._workspaces: List[Workspace] = load_workspaces()
        self._active_workspace: Workspace = self._workspaces[0]
        self._services: list[Service] = self._active_workspace.services
        self._active_service: Optional[Service] = None
        self._active_account: Optional[Account] = None

        # (service_id, account_id) → ServiceView
        self._views: Dict[Tuple[str, str], ServiceView] = {}
        # service_id → ServiceButton
        self._svc_btns: Dict[str, ServiceButton] = {}
        # group header widgets tracked for cleanup
        self._group_header_widgets: list = []

        # DND state — must be before _setup_tray()
        self._dnd_until: Optional[float] = None
        self._dnd_check_timer = QTimer(self)
        self._dnd_check_timer.timeout.connect(self._update_dnd_ui)
        self._dnd_check_timer.start(60_000)

        # Recent services (quick switch)
        self._recent_services: list[str] = []
        self._service_start_time: Optional[float] = None

        # Detached / PiP windows
        self._detached_windows: list = []
        self._pip_windows: list = []
        self._notif_history_dlg = None
        self._privacy_mode: bool = False

        self._setup_window()
        self._sidebar_compact: bool = load_settings().get('sidebar_compact', False)
        self._hover_anims: list = []
        self._build_ui()
        self._setup_tray()
        self._setup_shortcuts()
        self._rich_tooltip = _RichTooltip()
        self._hibernate_timers: Dict[str, 'QTimer'] = {}
        self._hibernated: set = set()  # set of (service_id, account_id) keys
        self._setup_hibernate_timers()
        self._apply_theme(self._theme)

        # Restore AI sidebar state from settings
        if load_settings().get('ai_sidebar_open', False):
            self._toggle_ai_sidebar()

        # Feature 3: fade animation on stack
        self._stack_effect = QGraphicsOpacityEffect(self._stack)
        self._stack.setGraphicsEffect(self._stack_effect)
        self._fade_anim = QPropertyAnimation(self._stack_effect, b'opacity', self)
        self._fade_anim.setDuration(150)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Feature 4: icon fetcher
        self._icon_fetcher = IconFetcher(self)
        self._icon_fetcher.fetched.connect(self._on_icon_fetched)
        self._fetch_service_icons()

        if self._services:
            self._select_service(self._services[0])

        set_ad_block(load_settings().get('ad_block', True))
        self._check_updates(silent=True)

        # ── Lock screen ──────────────────────────────────────────────────────
        settings = load_settings()
        pin_hash = settings.get('pin_hash')
        if pin_hash:
            self._lock_screen = LockScreen(pin_hash, self)
            self._lock_screen.setGeometry(self.rect())
            self._lock_screen.unlocked.connect(self._lock_screen.hide)
            self._lock_screen.show()
            self._lock_screen.raise_()
        else:
            self._lock_screen = None

        # Activity tracking for auto-lock
        self._last_activity = time.time()
        self.installEventFilter(self)
        self._auto_lock_timer = QTimer(self)
        self._auto_lock_timer.timeout.connect(self._check_auto_lock)
        self._auto_lock_timer.start(60_000)

        # ── Workspace schedule ───────────────────────────────────────────────
        from .workspace_schedule import load_schedule, get_active_workspace_id as _get_active_ws_id
        self._ws_schedule = load_schedule()
        self._schedule_timer = QTimer(self)
        self._schedule_timer.setInterval(60_000)
        self._schedule_timer.timeout.connect(self._check_workspace_schedule)
        self._schedule_timer.start()

        # ── Pop-out windows list ─────────────────────────────────────────────
        self._popout_windows: list = []

        # ── URL scheme registry ──────────────────────────────────────────────
        self._register_url_scheme()

        # ── Onboarding ───────────────────────────────────────────────────────
        if not load_settings().get('onboarding_done', False):
            QTimer.singleShot(200, self._show_onboarding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_lock_screen') and self._lock_screen and self._lock_screen.isVisible():
            self._lock_screen.setGeometry(self.rect())
        self._update_privacy_overlay_size()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress):
            self._last_activity = time.time()
        return super().eventFilter(obj, event)

    # ── window setup ─────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        sc = load_shortcuts()
        for i in range(9):
            s = QShortcut(QKeySequence(f'Ctrl+{i+1}'), self)
            s.activated.connect(lambda idx=i: self._kbd_select_service(idx))
        self._sc_objects = {}  # keep references to avoid GC
        for action, method in [
            ('focus_mode',  self._toggle_focus_mode),
            ('palette',     self._show_palette),
            ('zoom_in',     self._zoom_in),
            ('zoom_out',    self._zoom_out),
            ('zoom_reset',  self._zoom_reset),
            ('dnd_toggle',  self._toggle_dnd_shortcut),
        ]:
            key = sc.get(action, '')
            if key:
                s = QShortcut(QKeySequence(key), self)
                s.activated.connect(method)
                self._sc_objects[action] = s
        # Quick switch — handle separately since it's a Qt key combo
        qs_key = sc.get('quick_switch', 'Alt+`')
        try:
            s = QShortcut(QKeySequence(qs_key), self)
            s.activated.connect(self._quick_switch)
            self._sc_objects['quick_switch'] = s
        except Exception:
            s = QShortcut(QKeySequence(Qt.ALT | Qt.Key_QuoteLeft), self)
            s.activated.connect(self._quick_switch)
            self._sc_objects['quick_switch'] = s
        # Lock screen shortcut (Ctrl+L)
        lock_sc = QShortcut(QKeySequence('Ctrl+L'), self)
        lock_sc.activated.connect(self._lock_now)
        self._sc_objects['lock'] = lock_sc

        # Shortcuts cheatsheet
        shortcuts_sc = QShortcut(QKeySequence('Ctrl+?'), self)
        shortcuts_sc.activated.connect(self._show_shortcuts)
        self._sc_objects['shortcuts'] = shortcuts_sc

        # Privacy mode (Ctrl+Shift+P)
        privacy_sc = QShortcut(QKeySequence('Ctrl+Shift+P'), self)
        privacy_sc.activated.connect(self._toggle_privacy_mode)
        self._sc_objects['privacy'] = privacy_sc

        # AI sidebar (Ctrl+Shift+A)
        ai_sc = QShortcut(QKeySequence('Ctrl+Shift+A'), self)
        ai_sc.activated.connect(self._toggle_ai_sidebar)
        self._sc_objects['ai_sidebar'] = ai_sc

    def _kbd_select_service(self, idx: int):
        if idx < len(self._services):
            self._select_service(self._services[idx])

    def _toggle_focus_mode(self):
        self._sidebar.setVisible(not self._sidebar.isVisible())
        if self._active_service:
            self._refresh_header()

    def _zoom_in(self):
        self._set_zoom(min(3.0, (self._active_service.zoom if self._active_service else 1.0) + 0.1))

    def _zoom_out(self):
        self._set_zoom(max(0.3, (self._active_service.zoom if self._active_service else 1.0) - 0.1))

    def _zoom_reset(self):
        self._set_zoom(1.0)

    def _set_zoom(self, factor: float):
        if not self._active_service or not self._active_account:
            return
        self._active_service.zoom = round(factor, 2)
        key = (self._active_service.id, self._active_account.id)
        if key in self._views:
            self._views[key].set_zoom(factor)
        self._save()

    def _setup_window(self):
        self.setWindowTitle('Orbit')
        self.resize(1440, 940)
        self.setMinimumSize(900, 600)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        settings = load_settings()
        if 'geometry' in settings:
            g = settings['geometry']
            self.setGeometry(g['x'], g['y'], g['w'], g['h'])
        self._theme = settings.get('theme', 'dark')
        self._accent = settings.get('accent', 'Iris')

    # ── UI construction ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SIDEBAR ────────────────────────────────────────────────────────────
        ws_accent = getattr(self._active_workspace, 'accent', '')
        _sidebar_accent = ws_accent if ws_accent else ACCENTS.get(self._accent, ACCENTS['Iris'])
        self._sidebar = _GlassSidebar(_sidebar_accent)
        self._glass_sidebar = self._sidebar
        self._sidebar.setMinimumWidth(64)

        sb_layout = QVBoxLayout(self._sidebar)
        sb_layout.setContentsMargins(0, 12, 0, 8)
        sb_layout.setSpacing(0)

        logo = QLabel('🐙')
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(36)
        logo.setStyleSheet('font-size:22px;')
        sb_layout.addWidget(logo)
        sb_layout.addSpacing(8)

        # Workspace switcher
        self._ws_btn = QPushButton()
        self._ws_btn.setObjectName('wsBtn')
        self._ws_btn.setFixedHeight(24)
        self._ws_btn.setCursor(Qt.PointingHandCursor)
        self._ws_btn.setToolTip('Trocar workspace')
        self._ws_btn.clicked.connect(self._show_workspace_menu)
        self._ws_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self._ws_btn.customContextMenuRequested.connect(
            lambda pos: self._show_workspace_ctx_menu(self._ws_btn.mapToGlobal(pos))
        )
        sb_layout.addWidget(self._ws_btn)
        sb_layout.addSpacing(4)

        # Separator between workspace button and service list
        _sep_top = QFrame()
        _sep_top.setFixedHeight(1)
        _sep_top.setStyleSheet('background-color: #2e2e3d; border: none; margin: 2px 8px;')
        sb_layout.addWidget(_sep_top)
        sb_layout.addSpacing(4)
        scroll = QScrollArea()
        scroll.setObjectName('svcScroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._svc_container = QWidget()
        self._svc_container.setObjectName('svcContainer')
        self._svc_container.setAcceptDrops(True)
        self._svc_container.dragEnterEvent = self._svc_drag_enter
        self._svc_container.dropEvent = self._svc_drop
        self._svc_layout = QVBoxLayout(self._svc_container)
        self._svc_layout.setContentsMargins(6, 4, 6, 4)
        self._svc_layout.setSpacing(1)
        self._svc_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self._svc_container)
        sb_layout.addWidget(scroll, 1)

        # Separator between service list and bottom buttons
        _sep_bot = QFrame()
        _sep_bot.setFixedHeight(1)
        _sep_bot.setStyleSheet('background-color: #2e2e3d; border: none; margin: 2px 8px;')
        sb_layout.addWidget(_sep_bot)

        # Add button
        add_btn_wrap = QWidget()
        add_layout = QHBoxLayout(add_btn_wrap)
        add_layout.setContentsMargins(8, 0, 8, 0)
        add_layout.addStretch()
        add_btn = QPushButton()
        add_btn.setIcon(svg_icon('plus-circle', 20, '#6c7086'))
        add_btn.setIconSize(QSize(20, 20))
        add_btn.setObjectName('addBtn')
        add_btn.setFixedSize(52, 44)
        add_btn.setToolTip('Adicionar serviço')
        add_btn.clicked.connect(self._add_service)
        add_layout.addWidget(add_btn)
        add_layout.addStretch()
        sb_layout.addWidget(add_btn_wrap)

        # Compact toggle button
        compact_wrap = QWidget()
        compact_layout = QHBoxLayout(compact_wrap)
        compact_layout.setContentsMargins(8, 0, 8, 4)
        compact_layout.addStretch()
        self._compact_btn = QPushButton()
        self._compact_btn.setIcon(svg_icon('chevron-double-left' if not self._sidebar_compact else 'chevron-double-right', 16, '#6c7086'))
        self._compact_btn.setIconSize(QSize(16, 16))
        self._compact_btn.setObjectName('addBtn')
        self._compact_btn.setFixedSize(52, 28)
        self._compact_btn.setCursor(Qt.PointingHandCursor)
        self._compact_btn.setToolTip('Alternar sidebar compacta')
        self._compact_btn.clicked.connect(self._toggle_compact)
        compact_layout.addWidget(self._compact_btn)
        compact_layout.addStretch()
        sb_layout.addWidget(compact_wrap)

        # ── CONTENT AREA ───────────────────────────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self._header = QWidget()
        self._header.setObjectName('header')
        self._header.setFixedHeight(44)
        self._header_layout = QHBoxLayout(self._header)
        self._header_layout.setContentsMargins(10, 0, 10, 0)
        self._header_layout.setSpacing(6)
        self._status_badge = _StatusBadge()
        content_layout.addWidget(self._header)

        sep = QFrame()
        sep.setObjectName('hSep')
        sep.setFrameShape(QFrame.HLine)
        content_layout.addWidget(sep)

        # Stacked webviews + welcome
        self._stack = QStackedWidget()
        self._stack.setObjectName('stack')
        self._welcome = self._make_welcome()
        self._stack.addWidget(self._welcome)
        self._dashboard = DashboardWidget(self._services)
        self._dashboard.service_clicked.connect(self._select_service_by_id)
        self._stack.addWidget(self._dashboard)
        content_layout.addWidget(self._stack, 1)

        # Privacy overlay — child of stack, floats above web content
        self._privacy_overlay = _PrivacyOverlay(self._stack)

        # Feature 2: QSplitter for resizable sidebar
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.addWidget(self._sidebar)
        self._splitter.addWidget(content)
        self._ai_panel = self._build_ai_sidebar()
        self._splitter.addWidget(self._ai_panel)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._splitter.setCollapsible(2, True)
        saved_w = load_settings().get('sidebar_width', 220 if not self._sidebar_compact else 68)
        self._splitter.setSizes([saved_w, 1220, 0])
        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        root.addWidget(self._splitter, 1)

        self._rebuild_sidebar()
        self._update_workspace_btn()

    def _build_ai_sidebar(self) -> QWidget:
        """Placeholder AI sidebar panel (collapsed by default)."""
        panel = QWidget()
        panel.setObjectName('aiPanel')
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(0)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        return panel

    def _toggle_ai_sidebar(self):
        """Toggle the AI sidebar panel open/closed."""
        if not hasattr(self, '_ai_panel'):
            return
        sizes = self._splitter.sizes()
        if len(sizes) >= 3:
            new_ai = 0 if sizes[2] > 0 else 320
            self._splitter.setSizes([sizes[0], sizes[1] - new_ai, new_ai])

    def _make_welcome(self) -> QWidget:
        w = QWidget()
        w.setObjectName('welcome')
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        logo = QLabel('🐙')
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet('font-size:64px;')
        layout.addWidget(logo)

        title = QLabel('Orbit')
        title.setObjectName('wTitle')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel('Adicione um serviço para começar.\nSuporta Slack, WhatsApp, Telegram, Gmail e mais.')
        sub.setObjectName('wSub')
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(8)

        btn = QPushButton('+ Adicionar serviço')
        btn.setObjectName('primaryButton')
        btn.setFixedWidth(200)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._add_service)
        layout.addWidget(btn, 0, Qt.AlignCenter)

        return w

    # ── AI sidebar ────────────────────────────────────────────────────────────

    _AI_URLS = {
        'ChatGPT': 'https://chat.openai.com',
        'Claude': 'https://claude.ai',
        'Gemini': 'https://gemini.google.com',
        'Perplexity': 'https://www.perplexity.ai',
    }

    def _build_ai_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName('aiSidebar')
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(0)  # hidden by default

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setObjectName('aiHeader')
        header.setFixedHeight(40)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(8, 0, 8, 0)

        lbl = QLabel('🤖 IA')
        lbl.setStyleSheet('font-weight: bold; font-size: 13px;')
        hlay.addWidget(lbl)

        self._ai_provider_combo = QComboBox()
        self._ai_provider_combo.addItems(list(self._AI_URLS.keys()))
        self._ai_provider_combo.setFixedWidth(110)
        self._ai_provider_combo.currentIndexChanged.connect(self._on_ai_provider_changed)
        hlay.addWidget(self._ai_provider_combo)

        hlay.addStretch()

        close_btn = QPushButton('✕')
        close_btn.setObjectName('iconBtn')
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self._toggle_ai_sidebar)
        hlay.addWidget(close_btn)

        lay.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        # WebView — imported lazily so tests without QtWebEngine still work
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._ai_view = QWebEngineView()
            self._ai_view.load(QUrl('https://chat.openai.com'))
            lay.addWidget(self._ai_view, 1)
        except Exception:
            fallback = QLabel('🤖\nWebEngine não disponível')
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet('color: #6c7086; font-size: 13px;')
            self._ai_view = None
            lay.addWidget(fallback, 1)

        return panel

    def _on_ai_provider_changed(self, index: int):
        if not hasattr(self, '_ai_view') or self._ai_view is None:
            return
        provider = self._ai_provider_combo.currentText()
        url = self._AI_URLS.get(provider, 'https://chat.openai.com')
        self._ai_view.load(QUrl(url))

    def _toggle_ai_sidebar(self):
        panel = self._ai_panel
        is_visible = panel.maximumWidth() > 0
        if is_visible:
            panel.setMaximumWidth(0)
            panel.setMinimumWidth(0)
        else:
            panel.setMinimumWidth(380)
            panel.setMaximumWidth(600)
        settings = load_settings()
        settings['ai_sidebar_open'] = not is_visible
        save_settings(settings)

    # ── privacy mode ──────────────────────────────────────────────────────────

    def _toggle_privacy_mode(self):
        self._privacy_mode = not self._privacy_mode
        if self._privacy_mode:
            self._privacy_overlay.show()
            self._privacy_overlay.raise_()
            self._privacy_overlay.resize(self._stack.size())
        else:
            self._privacy_overlay.hide()
        if hasattr(self, '_tray_privacy_act'):
            self._tray_privacy_act.setChecked(self._privacy_mode)

    def _update_privacy_overlay_size(self):
        if hasattr(self, '_privacy_overlay'):
            self._privacy_overlay.resize(self._stack.size())

    # ── sidebar ───────────────────────────────────────────────────────────────

    def _rebuild_sidebar(self):
        # Clear ALL widgets from the service layout (buttons + group headers + wrappers)
        while self._svc_layout.count():
            item = self._svc_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._svc_btns.clear()
        self._group_header_widgets = []
        self._hover_anims = []

        from .catalog import get_entry

        groups = getattr(self._active_workspace, 'groups', [])
        grouped_ids: set = set()
        for g in groups:
            grouped_ids.update(g.service_ids)

        def _add_service_btn(svc: Service, indent: int = 0):
            btn = ServiceButton(svc, compact=self._sidebar_compact)
            if self._sidebar_compact:
                btn.setToolTip(svc.name)
            from .brand_icons import brand_icon, has_brand_icon
            entry = get_entry(svc.service_type)
            if has_brand_icon(svc.service_type):
                px = brand_icon(svc.service_type, 24)
                if not px.isNull():
                    btn.set_pixmap(px)
            elif entry and entry.favicon_url:
                cached = get_cached_pixmap(entry.favicon_url)
                if cached:
                    btn.set_pixmap(cached)
            btn.clicked.connect(lambda _, s=svc: self._select_service(s))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, s=svc: self._show_ctx_menu(s, b.mapToGlobal(pos))
            )
            btn.hovered.connect(
                lambda is_hovered, s=svc, b=btn:
                    self._rich_tooltip.show_for(s, b.mapToGlobal(b.rect()).translated(b.width(), 0))
                    if is_hovered else self._rich_tooltip.hide()
            )
            if indent > 0 and not self._sidebar_compact:
                wrap = QWidget()
                wrap_lay = QHBoxLayout(wrap)
                wrap_lay.setContentsMargins(indent, 0, 0, 0)
                wrap_lay.setSpacing(0)
                wrap_lay.addWidget(btn)
                wrap.setFixedHeight(52)
                self._svc_layout.addWidget(wrap)
            elif self._sidebar_compact:
                self._svc_layout.addWidget(btn, 0, Qt.AlignHCenter)
            else:
                self._svc_layout.addWidget(btn)
            self._svc_btns[svc.id] = btn
            self._hover_anims.append(apply_hover_effect(btn, hover=1.0, normal=0.82))

        # Render groups
        for group in groups:
            header = self._make_group_header(group)
            self._svc_layout.addWidget(header)
            self._group_header_widgets.append(header)
            if not group.collapsed:
                for svc_id in group.service_ids:
                    svc = next((s for s in self._services if s.id == svc_id), None)
                    if svc:
                        _add_service_btn(svc, indent=8)

        # Ungrouped services
        for svc in self._services:
            if svc.id not in grouped_ids:
                _add_service_btn(svc, indent=0)

        if hasattr(self, '_icon_fetcher'):
            self._fetch_service_icons()

        if hasattr(self, '_dashboard'):
            self._dashboard.refresh(self._services)
            if not self._active_service:
                if self._services:
                    self._stack.setCurrentWidget(self._dashboard)
                else:
                    self._stack.setCurrentWidget(self._welcome)

    def _make_group_header(self, group: ServiceGroup) -> QWidget:
        header = QWidget()
        header.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        arrow_lbl = QLabel('▼' if not group.collapsed else '▶')
        arrow_lbl.setStyleSheet('color: #6c7086; font-size: 10px;')
        layout.addWidget(arrow_lbl)

        name_lbl = QLabel(group.name.upper())
        name_lbl.setStyleSheet('color: #6c7086; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;')
        layout.addWidget(name_lbl, 1)

        header.mousePressEvent = lambda e, g=group: self._toggle_group(g)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(
            lambda pos, g=group, h=header: self._show_group_ctx_menu(g, h.mapToGlobal(pos))
        )
        return header

    def _toggle_group(self, group: ServiceGroup):
        group.collapsed = not group.collapsed
        self._save()
        self._rebuild_sidebar()

    def _show_group_ctx_menu(self, group: ServiceGroup, global_pos):
        menu = QMenu(self)
        rename_act = menu.addAction('✏️ Renomear grupo')
        remove_act = menu.addAction('🗑️ Remover grupo')
        action = menu.exec(global_pos)
        if action == rename_act:
            self._rename_group(group)
        elif action == remove_act:
            self._remove_group(group)

    def _rename_group(self, group: ServiceGroup):
        name, ok = QInputDialog.getText(self, 'Renomear grupo', 'Novo nome:', text=group.name)
        if ok and name.strip():
            group.name = name.strip()
            self._save()
            self._rebuild_sidebar()

    def _remove_group(self, group: ServiceGroup):
        self._active_workspace.groups.remove(group)
        self._save()
        self._rebuild_sidebar()

    def _create_group_for(self, svc: Service):
        import uuid
        name, ok = QInputDialog.getText(self, 'Criar grupo', 'Nome do grupo:')
        if ok and name.strip():
            group = ServiceGroup(id=str(uuid.uuid4()), name=name.strip(), service_ids=[svc.id])
            self._active_workspace.groups.append(group)
            self._save()
            self._rebuild_sidebar()

    def _move_to_group(self, svc: Service, group_id):
        for g in self._active_workspace.groups:
            if svc.id in g.service_ids:
                g.service_ids.remove(svc.id)
        if group_id:
            target = next((g for g in self._active_workspace.groups if g.id == group_id), None)
            if target and svc.id not in target.service_ids:
                target.service_ids.append(svc.id)
        self._save()
        self._rebuild_sidebar()

    def _toggle_compact(self):
        self._sidebar_compact = not self._sidebar_compact
        settings = load_settings()
        settings['sidebar_compact'] = self._sidebar_compact
        save_settings(settings)

        target_w = 68 if self._sidebar_compact else 160
        start_w = self._splitter.sizes()[0]
        steps = 12
        delta = (target_w - start_w) / steps
        self._compact_step = 0
        self._compact_start = start_w
        self._compact_delta = delta
        self._compact_target = target_w

        if hasattr(self, '_compact_timer') and self._compact_timer.isActive():
            self._compact_timer.stop()
        self._compact_timer = QTimer(self)
        self._compact_timer.timeout.connect(self._animate_compact_step)
        self._compact_timer.start(12)

    def _animate_compact_step(self):
        self._compact_step += 1
        w = int(self._compact_start + self._compact_delta * self._compact_step)
        total = sum(self._splitter.sizes())
        self._splitter.setSizes([w, total - w])
        if self._compact_step >= 12:
            self._compact_timer.stop()
            total = sum(self._splitter.sizes())
            self._splitter.setSizes([self._compact_target, total - self._compact_target])
            self._rebuild_sidebar()
            self._update_compact_btn()

    def _update_compact_btn(self):
        if hasattr(self, '_compact_btn'):
            icon_name = 'chevron-double-right' if self._sidebar_compact else 'chevron-double-left'
            self._compact_btn.setIcon(svg_icon(icon_name, 14, '#6e6e8a'))
            self._compact_btn.setIconSize(QSize(14, 14))

    def _on_splitter_moved(self, pos: int, index: int):
        sizes = self._splitter.sizes()
        settings = load_settings()
        settings['sidebar_width'] = sizes[0]
        save_settings(settings)

    def _fetch_service_icons(self):
        from .catalog import get_entry
        seen_urls: set = set()
        for svc in self._services:
            entry = get_entry(svc.service_type)
            if entry and entry.favicon_url and entry.favicon_url not in seen_urls:
                seen_urls.add(entry.favicon_url)
                self._icon_fetcher.fetch(entry.favicon_url)

    def _on_icon_fetched(self, url: str, pixmap: QPixmap):
        from .catalog import get_entry
        for svc in self._services:
            entry = get_entry(svc.service_type)
            if entry and entry.favicon_url == url:
                btn = self._svc_btns.get(svc.id)
                if btn:
                    btn.set_pixmap(pixmap)

    # ── workspace ────────────────────────────────────────────────────────────

    def _apply_theme(self, theme: str):
        self._theme = theme
        accent_color = ACCENTS.get(self._accent, ACCENTS['Iris'])
        # Use workspace-specific accent if set
        ws_accent = getattr(getattr(self, '_active_workspace', None), 'accent', '')
        if ws_accent:
            accent_color = ws_accent
        tokens = get_tokens(theme, accent_color)
        self.setStyleSheet(tokens.qss())
        settings = load_settings()
        settings['theme'] = theme
        save_settings(settings)
        if hasattr(self, '_glass_sidebar'):
            self._glass_sidebar.set_accent(accent_color)
            self._glass_sidebar.setStyleSheet(
                'QWidget#sidebar { background: transparent; border-right: none; }'
            )

    def _set_accent(self, name: str):
        self._accent = name
        s = load_settings()
        s['accent'] = name
        save_settings(s)
        self._apply_theme(self._theme)
        ToastManager.show(self, f'Tema {name} aplicado!', 'success')

    def _update_workspace_btn(self):
        name = self._active_workspace.name
        fm = self._ws_btn.fontMetrics()
        available = self._ws_btn.width() - 20  # account for padding
        if available < 30:
            available = 100  # fallback before first paint
        elided = fm.elidedText(name, Qt.ElideRight, available)
        self._ws_btn.setText(f'{elided} ▾')

    def _show_workspace_menu(self):
        menu = QMenu(self)
        for ws in self._workspaces:
            act = menu.addAction(ws.name)
            act.setCheckable(True)
            act.setChecked(ws.id == self._active_workspace.id)
            act.triggered.connect(lambda _, w=ws: self._switch_workspace(w))
        menu.addSeparator()
        menu.addAction('＋ Novo workspace').triggered.connect(self._add_workspace)
        menu.exec(self._ws_btn.mapToGlobal(self._ws_btn.rect().bottomLeft()))

    def _show_workspace_ctx_menu(self, global_pos):
        menu = QMenu(self)
        rename_act = menu.addAction('✏  Renomear workspace')
        rename_act.triggered.connect(self._rename_workspace)
        delete_act = menu.addAction('🗑  Excluir workspace')
        delete_act.setEnabled(len(self._workspaces) > 1)
        delete_act.triggered.connect(self._delete_workspace)
        menu.exec(global_pos)

    def _switch_workspace(self, ws: Workspace):
        if ws.id == self._active_workspace.id:
            return
        self._active_workspace = ws
        self._services = ws.services
        self._active_service = None
        self._active_account = None
        self._rebuild_sidebar()
        self._update_workspace_btn()
        if self._services:
            self._stack.setCurrentWidget(self._dashboard)
        else:
            self._stack.setCurrentWidget(self._welcome)
        self._refresh_header()
        self._update_title_badge()
        if self._services:
            self._select_service(self._services[0])
        # Apply workspace-specific accent (or fall back to global)
        global_accent = ACCENTS.get(self._accent, ACCENTS['Iris'])
        effective_accent = ws.accent if ws.accent else global_accent
        tokens = get_tokens(self._theme, effective_accent)
        self.setStyleSheet(tokens.qss())
        if hasattr(self, '_glass_sidebar'):
            self._glass_sidebar.set_accent(effective_accent)
            self._glass_sidebar.setStyleSheet(
                'QWidget#sidebar { background: transparent; border-right: none; }'
            )

    def _add_workspace(self):
        from .models import new_id
        dlg = EditWorkspaceDialog(parent=self)
        dlg.setWindowTitle('Novo workspace')
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.get_name()
        if name:
            ws = Workspace(id=new_id('ws'), name=name, accent=dlg.get_accent())
            self._workspaces.append(ws)
            self._switch_workspace(ws)
            self._save()

    def _rename_workspace(self):
        dlg = EditWorkspaceDialog(
            name=self._active_workspace.name,
            accent=self._active_workspace.accent,
            parent=self,
        )
        dlg.setWindowTitle('Editar workspace')
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.get_name()
        if name:
            self._active_workspace.name = name
            self._active_workspace.accent = dlg.get_accent()
            self._update_workspace_btn()
            # Re-apply accent for the active workspace
            global_accent = ACCENTS.get(self._accent, ACCENTS['Iris'])
            effective_accent = self._active_workspace.accent if self._active_workspace.accent else global_accent
            tokens = get_tokens(self._theme, effective_accent)
            self.setStyleSheet(tokens.qss())
            if hasattr(self, '_glass_sidebar'):
                self._glass_sidebar.set_accent(effective_accent)
                self._glass_sidebar.setStyleSheet(
                    'QWidget#sidebar { background: transparent; border-right: none; }'
                )
            self._save()

    def _delete_workspace(self):
        if len(self._workspaces) <= 1:
            return
        dlg = ConfirmDialog(f'Excluir workspace "{self._active_workspace.name}" e todos os seus serviços?', self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._workspaces.remove(self._active_workspace)
        self._switch_workspace(self._workspaces[0])
        self._save()

    # ── header ────────────────────────────────────────────────────────────────

    def _refresh_header(self):
        while self._header_layout.count():
            item = self._header_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._status_badge:
                w.deleteLater()

        svc = self._active_service
        if not svc:
            return

        # Icon
        self._header_layout.addWidget(_IconLabel(svc, 24))

        # Name
        name = QLabel(svc.name)
        name.setObjectName('svcName')
        self._header_layout.addWidget(name)

        # Status badge (after name)
        self._header_layout.addWidget(self._status_badge)

        # Account tabs
        for acc in svc.accounts:
            tab = QPushButton(acc.label)
            tab.setObjectName('accTab')
            tab.setCheckable(True)
            tab.setCursor(Qt.PointingHandCursor)
            if self._active_account and acc.id == self._active_account.id:
                tab.setChecked(True)
            tab.clicked.connect(lambda _, a=acc: self._select_account(a))
            self._header_layout.addWidget(tab)

        self._header_layout.addStretch()

        # Privacy mode button
        privacy_btn = QPushButton('👁')
        privacy_btn.setObjectName('hBtn')
        privacy_btn.setFixedSize(28, 28)
        privacy_btn.setToolTip('Modo Privacidade (Ctrl+Shift+P)')
        privacy_btn.setCursor(Qt.PointingHandCursor)
        privacy_btn.setCheckable(True)
        privacy_btn.setChecked(self._privacy_mode)
        privacy_btn.clicked.connect(self._toggle_privacy_mode)
        self._header_layout.addWidget(privacy_btn)

        # AI sidebar toggle button
        ai_btn = QPushButton('🤖')
        ai_btn.setObjectName('hBtn')
        ai_btn.setFixedSize(28, 28)
        ai_btn.setToolTip('Painel IA (Ctrl+Shift+A)')
        ai_btn.setCursor(Qt.PointingHandCursor)
        ai_btn.clicked.connect(self._toggle_ai_sidebar)
        self._header_layout.addWidget(ai_btn)

        # Notification history button
        hist_btn = QPushButton()
        hist_btn.setIcon(svg_icon('bell', 16, '#6c7086'))
        hist_btn.setIconSize(QSize(16, 16))
        hist_btn.setObjectName('hBtn')
        hist_btn.setFixedSize(28, 28)
        hist_btn.setToolTip('Histórico de notificações')
        hist_btn.setCursor(Qt.PointingHandCursor)
        hist_btn.clicked.connect(self._show_notif_history_panel)
        self._header_layout.addWidget(hist_btn)

        # DND button
        dnd_icon = 'bell-slash' if self._is_dnd_active() else 'bell'
        dnd_btn = QPushButton()
        dnd_btn.setIcon(svg_icon(dnd_icon, 16, '#6c7086'))
        dnd_btn.setIconSize(QSize(16, 16))
        dnd_btn.setObjectName('hBtn')
        dnd_btn.setFixedSize(28, 28)
        dnd_btn.setToolTip('Não perturbe')
        dnd_btn.setCursor(Qt.PointingHandCursor)
        dnd_btn.clicked.connect(self._show_dnd_menu)
        self._header_layout.addWidget(dnd_btn)

        # Focus toggle button
        focus_icon = 'chevron-left' if self._sidebar.isVisible() else 'chevron-right'
        focus_btn = QPushButton()
        focus_btn.setIcon(svg_icon(focus_icon, 16, '#6c7086'))
        focus_btn.setIconSize(QSize(16, 16))
        focus_btn.setObjectName('hBtn')
        focus_btn.setFixedSize(28, 28)
        focus_btn.setToolTip('Modo foco (Ctrl+B)')
        focus_btn.setCursor(Qt.PointingHandCursor)
        focus_btn.clicked.connect(self._toggle_focus_mode)
        self._header_layout.addWidget(focus_btn)

        # Action buttons
        for icon_name, tip, slot in [
            ('arrow-top-right-on-square', 'Abrir em janela', lambda: self._open_in_window(svc, self._active_account) if self._active_account else None),
            ('rectangle-stack', 'Picture-in-Picture', lambda: self._open_pip(svc, self._active_account) if self._active_account else None),
            ('plus',  'Adicionar conta',   self._add_account),
            ('cog-6-tooth',  'Configurar',        lambda: self._configure(svc)),
            ('trash',  'Remover serviço',  lambda: self._remove_service(svc)),
        ]:
            is_danger = icon_name == 'trash'
            name_id = 'hDanger' if is_danger else 'hBtn'
            ic_color = '#f38ba8' if is_danger else '#6c7086'
            b = QPushButton()
            b.setIcon(svg_icon(icon_name, 16, ic_color))
            b.setIconSize(QSize(16, 16))
            b.setObjectName(name_id)
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            self._header_layout.addWidget(b)

    # ── selection ─────────────────────────────────────────────────────────────

    def _select_service(self, service: Service):
        # Record time on previous service
        if self._active_service and self._service_start_time:
            elapsed = time.time() - self._service_start_time
            record_session(self._active_service.id, self._active_service.name, elapsed)
        self._service_start_time = time.time()
        self._active_service = service
        self._reset_hibernate_timer(service)
        for sid, btn in self._svc_btns.items():
            btn.setChecked(sid == service.id)
            btn.set_active(sid == service.id)
        # Update recent services list (quick switch)
        svc_id = service.id
        if svc_id in self._recent_services:
            self._recent_services.remove(svc_id)
        self._recent_services.insert(0, svc_id)
        self._recent_services = self._recent_services[:10]
        self._update_title()
        if service.accounts:
            self._select_account(service.accounts[0])
        else:
            self._active_account = None
            self._refresh_header()
        self._save()

    def _select_account(self, account: Account):
        if not self._active_service:
            return
        self._active_account = account
        key = (self._active_service.id, account.id)

        # Feature: proxy per service — set application proxy before creating view
        from PySide6.QtNetwork import QNetworkProxy
        proxy_str = getattr(self._active_service, 'proxy', '')
        if proxy_str:
            from urllib.parse import urlparse
            p = urlparse(proxy_str)
            qt_proxy = QNetworkProxy()
            qt_proxy.setType(
                QNetworkProxy.ProxyType.Socks5Proxy
                if p.scheme == 'socks5'
                else QNetworkProxy.ProxyType.HttpProxy
            )
            qt_proxy.setHostName(p.hostname or '')
            qt_proxy.setPort(p.port or 8080)
            if p.username:
                qt_proxy.setUser(p.username)
            if p.password:
                qt_proxy.setPassword(p.password)
            QNetworkProxy.setApplicationProxy(qt_proxy)
        else:
            QNetworkProxy.setApplicationProxy(
                QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
            )

        if key not in self._views:
            view = ServiceView(account.profile_name, account.url,
                               service_type=self._active_service.service_type,
                               custom_css=self._active_service.custom_css,
                               custom_js=self._active_service.custom_js,
                               zoom=self._active_service.zoom,
                               incognito=getattr(self._active_service, 'incognito', False))
            view.badge_changed.connect(
                lambda count, svc=self._active_service: self._update_badge(svc, count)
            )
            view.load_status_changed.connect(
                lambda s, sid=self._active_service.id: self._on_load_status(sid, s)
            )
            self._views[key] = view
            self._stack.addWidget(view)
            self._status_badge.set_status('connecting')

        self._wake_service(self._active_service, account)
        self._stack.setCurrentWidget(self._views[key])

        # Update status badge for the now-active view
        view = self._views[key]
        self._status_badge.set_status('connecting' if view.status == 'idle' else view.status)
        try:
            view.load_status_changed.disconnect(self._on_active_load_status)
        except Exception:
            pass
        view.load_status_changed.connect(self._on_active_load_status)

        # Feature 3: fade-in transition
        if hasattr(self, '_fade_anim'):
            self._fade_anim.stop()
            self._fade_anim.start()
        self._refresh_header()
        self._save()

    def _update_badge(self, service: Service, count: int):
        prev = service.unread
        service.unread = count
        btn = self._svc_btns.get(service.id)
        if btn:
            btn.set_badge(count)
            if count > prev and count > 0:
                btn.pulse_badge()
        self._update_title_badge()
        if count > prev and count > 0:
            add_notification(service.id, service.name, f'{service.name}: {count} mensagem(s)')
            is_active = self._active_service and self._active_service.id == service.id
            if not is_active and hasattr(self, '_tray') and not self._is_dnd_active():
                self._tray.showMessage(
                    service.name,
                    f'{count} mensagem(ns) não lida(s)',
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
                if service.notification_sound:
                    play_sound(service.notification_sound)
        self._save()

    def _on_active_load_status(self, status: str):
        self._status_badge.set_status(
            'connecting' if status == 'loading' else
            'ready' if status == 'ready' else
            'error'
        )

    def _update_title(self):
        total_unread = sum(s.unread for s in self._services)
        svc_name = self._active_service.name if self._active_service else ''
        badge = f'({total_unread}) ' if total_unread > 0 else ''
        if svc_name:
            self.setWindowTitle(f'{badge}{svc_name} — Orbit')
        else:
            self.setWindowTitle(f'{badge}Orbit')

    def _update_title_badge(self):
        total = sum(s.unread for s in self._services)
        if hasattr(self, '_tray'):
            if total > 0:
                self._tray.setToolTip(f'Orbit — {total} não lida(s)')
            else:
                self._tray.setToolTip('Orbit')
        self._update_tray_badge()
        self._update_title()

    def _update_tray_badge(self):
        if not hasattr(self, '_tray'):
            return
        total = sum(getattr(s, 'unread', 0) for s in self._services)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.ico')
        base = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        if total <= 0:
            self._tray.setIcon(base)
            return
        px = base.pixmap(32, 32)
        if px.isNull():
            px = QPixmap(32, 32)
            px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        badge_text = str(total) if total <= 99 else '99+'
        bw = max(14, len(badge_text) * 6 + 4)
        bh = 14
        bx = 32 - bw
        by = 0
        p.setBrush(QBrush(QColor('#f38ba8')))
        p.setPen(Qt.NoPen)
        p.drawEllipse(bx, by, bw, bh)
        p.setPen(QPen(QColor('#1e1e2e')))
        p.setFont(QFont('Segoe UI', 7, QFont.Bold))
        p.drawText(bx, by, bw, bh, Qt.AlignCenter, badge_text)
        p.end()
        self._tray.setIcon(QIcon(px))

    def _on_load_status(self, service_id: str, status: str):
        btn = self._svc_btns.get(service_id)
        if btn:
            btn.set_status(status)

    # ── context menu ──────────────────────────────────────────────────────────

    def _show_ctx_menu(self, service: Service, global_pos):
        menu = QMenu(self)
        config_act = menu.addAction('Configurar')
        config_act.setIcon(svg_icon('cog-6-tooth', 14, '#6c7086'))
        add_acc_act = menu.addAction('Adicionar conta')
        add_acc_act.setIcon(svg_icon('plus', 14, '#6c7086'))
        open_win_act = menu.addAction('Abrir em janela')
        open_win_act.setIcon(svg_icon('arrow-top-right-on-square', 14, '#6c7086'))
        pip_act = menu.addAction('Picture-in-Picture')
        pip_act.setIcon(svg_icon('rectangle-stack', 14, '#6c7086'))

        is_google = any(t in service.service_type for t in _GOOGLE_TYPES)
        sync_act = None
        if is_google:
            menu.addSeparator()
            sync_act = menu.addAction('Sincronizar cookies do Chrome')
            sync_act.setIcon(svg_icon('arrow-path', 14, '#6c7086'))

        # Group actions
        menu.addSeparator()
        create_group_act = menu.addAction('Criar grupo...')
        create_group_act.setIcon(svg_icon('folder', 14, '#6c7086'))
        create_group_act.triggered.connect(lambda: self._create_group_for(service))

        groups = getattr(self._active_workspace, 'groups', [])
        if groups:
            move_menu = menu.addMenu('Mover para grupo...')
            move_menu.setIcon(svg_icon('folder', 14, '#6c7086'))
            for g in groups:
                act = move_menu.addAction(g.name)
                act.setCheckable(True)
                act.setChecked(service.id in g.service_ids)
                act.triggered.connect(lambda _, gid=g.id: self._move_to_group(service, gid))
            move_menu.addSeparator()
            no_group_act = move_menu.addAction('Sem grupo')
            no_group_act.triggered.connect(lambda: self._move_to_group(service, None))

        menu.addSeparator()
        remove_act = menu.addAction('Remover serviço')
        remove_act.setIcon(svg_icon('trash', 14, '#f38ba8'))

        # Pop-out action
        menu.addSeparator()
        popout_act = menu.addAction(svg_icon('arrow-top-right-on-square', 16, '#a6adc8'), 'Abrir em janela separada')
        popout_act.triggered.connect(lambda: self._popout_service(service))

        # Reading list action
        reading_act = menu.addAction(svg_icon('archive-box-arrow-down', 16, '#a6adc8'), 'Salvar URL na lista de leitura')

        def _save_url():
            key = (service.id, self._active_account.id if self._active_account else None)
            url = ''
            if key in self._views:
                url = self._views[key].url().toString()
            elif service.accounts:
                from .catalog import get_entry
                entry = get_entry(service.service_type)
                url = entry.default_url if entry else ''
            if url:
                from .reading_list import add_to_reading_list
                added = add_to_reading_list(url, service.name, service.name)
                if added:
                    ToastManager.show(self, 'URL salva na lista de leitura', 'success')
                else:
                    ToastManager.show(self, 'URL já está na lista', 'info')

        reading_act.triggered.connect(_save_url)

        action = menu.exec(global_pos)
        if action == config_act:
            self._select_service(service)
            self._configure(service)
        elif action == add_acc_act:
            self._select_service(service)
            self._add_account()
        elif action == open_win_act:
            if service.accounts:
                acc = (self._active_account if self._active_account and self._active_account in service.accounts
                       else service.accounts[0])
                self._open_in_window(service, acc)
        elif action == pip_act:
            if service.accounts:
                acc = (self._active_account if self._active_account and self._active_account in service.accounts
                       else service.accounts[0])
                self._open_pip(service, acc)
        elif sync_act and action == sync_act:
            self._select_service(service)
            self._sync_chrome_cookies(service)
        elif action == remove_act:
            self._remove_service(service)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _add_service(self):
        dlg = AddServiceDialog(self)
        if dlg.exec() == QDialog.Accepted:
            svc = dlg.get_service()
            if svc:
                self._services.append(svc)
                self._rebuild_sidebar()
                self._select_service(svc)
                self._save()

    def _add_account(self):
        if not self._active_service:
            return
        dlg = AddAccountDialog(self._active_service, self)
        if dlg.exec() == QDialog.Accepted:
            acc = dlg.get_account()
            if acc:
                self._active_service.accounts.append(acc)
                self._select_account(acc)
                self._save()

    def _configure(self, service: Service):
        old_css = service.custom_css
        old_js = service.custom_js
        dlg = ConfigDialog(service, self)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply_to(service)
            self._reset_hibernate_timer(service)
            self._rebuild_sidebar()
            self._refresh_header()
            if service.custom_css != old_css or service.custom_js != old_js:
                need_reselect = (self._active_service and self._active_service.id == service.id)
                active_acc = self._active_account
                for acc in service.accounts:
                    key = (service.id, acc.id)
                    if key in self._views:
                        view = self._views.pop(key)
                        self._stack.removeWidget(view)
                        view.deleteLater()
                if need_reselect and active_acc:
                    self._select_account(active_acc)
            self._save()

    def _remove_service(self, service: Service):
        dlg = ConfirmDialog(f'Remover "{service.name}" e todas as contas?', self)
        if dlg.exec() != QDialog.Accepted:
            return

        # Destroy views
        for acc in service.accounts:
            key = (service.id, acc.id)
            if key in self._views:
                view = self._views.pop(key)
                self._stack.removeWidget(view)
                view.deleteLater()

        self._services.remove(service)

        if self._active_service and self._active_service.id == service.id:
            self._active_service = None
            self._active_account = None
            if self._services and len(self._services) > 1:
                pass  # _rebuild_sidebar will show dashboard
            else:
                self._stack.setCurrentWidget(self._welcome)
            self._refresh_header()

        self._rebuild_sidebar()
        self._save()

        if self._services:
            self._select_service(self._services[0])

    # ── persistence ───────────────────────────────────────────────────────────

    def _save(self):
        save_workspaces(self._workspaces)

    # ── chrome cookie sync ────────────────────────────────────────────────────

    def _sync_chrome_cookies(self, service: Service):
        """Import Google cookies from any browser and reload views for this service."""
        import subprocess, time
        from PySide6.QtWidgets import QMessageBox
        from .cookie_bridge import find_all_browsers

        # Pick the best browser available
        all_browsers = find_all_browsers()
        if not all_browsers:
            QMessageBox.warning(self, 'Orbit',
                'Nenhum navegador compatível encontrado.\n\n'
                'Instale Chrome, Brave, Edge, Firefox ou Opera.')
            return

        # Use the first detected browser (Chromium priority, then Firefox)
        browser_info = all_browsers[0]
        browser_name = browser_info['name']
        browser_exe  = browser_info['exe']
        is_firefox   = browser_info['type'] == 'firefox'

        if not is_firefox and is_browser_running(browser_exe):
            reply = QMessageBox.question(
                self, 'Orbit — Sincronizar sessão',
                f'O {browser_name} está aberto e bloqueando o acesso aos cookies.\n\n'
                f'Deseja fechar o {browser_name} automaticamente para sincronizar?\n'
                f'Ele será fechado agora e você poderá reabri-lo depois.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            try:
                subprocess.run(['taskkill', '/IM', browser_exe, '/F'],
                               capture_output=True, timeout=10)
                for _ in range(10):
                    time.sleep(0.5)
                    if not is_browser_running(browser_exe):
                        break
                # Extra wait to ensure file locks are fully released
                time.sleep(1.5)
            except Exception:
                pass

            if is_browser_running(browser_exe):
                QMessageBox.warning(self, 'Orbit',
                    f'Não foi possível fechar o {browser_name}.\n'
                    f'Feche manualmente e tente novamente.')
                return

        total = 0
        for acc in service.accounts:
            key = (service.id, acc.id)
            if key in self._views:
                n = import_google_cookies(self._views[key]._profile)
                if n:
                    total += n
                    self._views[key].reload()

        if total > 0:
            msg = (f'✅ {total} cookies importados do {browser_name}.\n\n'
                   f'A página foi recarregada com sua sessão do Google.')
            if not is_firefox:
                msg += f'\nVocê já pode reabrir o {browser_name}.'
            QMessageBox.information(self, 'Orbit', msg)
        else:
            detected = ', '.join(b['name'] for b in all_browsers)
            QMessageBox.warning(self, 'Orbit',
                f'Nenhum cookie do Google encontrado.\n\n'
                f'Navegadores detectados: {detected}\n\n'
                f'Certifique-se de estar logado no Google em um desses navegadores.')

    # ── tray ──────────────────────────────────────────────────────────────────

    def _export_backup(self):
        import zipfile
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(
            self, 'Exportar configurações', 'orbit-backup.zip',
            'ZIP Files (*.zip)'
        )
        if not path:
            return
        from .storage import STORAGE_DIR, _WORKSPACES_FILE, _SETTINGS_FILE
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in ['workspaces.json', 'settings.json']:
                fpath = os.path.join(STORAGE_DIR, fname)
                if os.path.exists(fpath):
                    zf.write(fpath, fname)
        ToastManager.show(self, 'Backup exportado com sucesso!', 'success')

    def _import_backup(self):
        import zipfile
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self, 'Importar configurações', '', 'ZIP Files (*.zip)'
        )
        if not path:
            return
        from .storage import STORAGE_DIR
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                names = zf.namelist()
                if 'workspaces.json' not in names and 'settings.json' not in names:
                    QMessageBox.warning(self, 'Orbit', 'Arquivo inválido: não é um backup do Orbit.')
                    return
                zf.extractall(STORAGE_DIR)
            ToastManager.show(self, 'Configurações importadas. Reinicie para aplicar.', 'info')
        except Exception as e:
            QMessageBox.critical(self, 'Orbit', f'Erro ao importar: {e}')
            ToastManager.show(self, f'Erro ao importar: {e}', 'error')

    def _show_cloud_sync_dialog(self):
        import threading
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                                        QPushButton, QLabel, QHBoxLayout, QDialogButtonBox)
        settings = load_settings()
        dlg = QDialog(self)
        dlg.setWindowTitle('☁️ Sincronização na nuvem — GitHub Gist')
        dlg.setMinimumWidth(460)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel('☁️ Sincronização via GitHub Gist')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)

        hint = QLabel(
            'Use um Personal Access Token do GitHub com escopo <b>gist</b>.<br>'
            'Deixe o Gist ID vazio no primeiro uso — um novo Gist será criado.'
        )
        hint.setWordWrap(True)
        hint.setStyleSheet('font-size:11px; color:#6c7086;')
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)

        token_edit = QLineEdit(settings.get('gist_token', ''))
        token_edit.setPlaceholderText('ghp_...')
        token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Token GitHub', token_edit)

        gist_id_edit = QLineEdit(settings.get('gist_id', ''))
        gist_id_edit.setPlaceholderText('(vazio = criar novo Gist)')
        form.addRow('Gist ID', gist_id_edit)

        layout.addLayout(form)

        status_lbl = QLabel('')
        status_lbl.setWordWrap(True)
        status_lbl.setStyleSheet('font-size:12px;')
        layout.addWidget(status_lbl)

        btn_row = QHBoxLayout()
        upload_btn = QPushButton('☁️ Enviar para nuvem')
        upload_btn.setObjectName('primaryButton')
        download_btn = QPushButton('⬇️ Baixar da nuvem')
        download_btn.setObjectName('secondaryButton')
        btn_row.addWidget(upload_btn)
        btn_row.addWidget(download_btn)
        layout.addLayout(btn_row)

        close_btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btns.rejected.connect(dlg.reject)
        layout.addWidget(close_btns)

        def get_token():
            return token_edit.text().strip()

        def get_gist_id():
            return gist_id_edit.text().strip()

        def save_token_and_gist(token, gist_id):
            s = load_settings()
            s['gist_token'] = token
            s['gist_id'] = gist_id
            save_settings(s)

        def on_upload():
            token = get_token()
            if not token:
                status_lbl.setStyleSheet('color:#f38ba8; font-size:12px;')
                status_lbl.setText('❌ Informe o token GitHub.')
                return
            upload_btn.setEnabled(False)
            download_btn.setEnabled(False)
            status_lbl.setStyleSheet('color:#a6adc8; font-size:12px;')
            status_lbl.setText('Enviando...')
            gist_id = get_gist_id()

            def run():
                try:
                    from .storage import _WORKSPACES_FILE, _SETTINGS_FILE
                    import json as _json, os as _os
                    ws_data = _json.loads(open(_WORKSPACES_FILE, encoding='utf-8').read()) if _os.path.exists(_WORKSPACES_FILE) else []
                    s_data = _json.loads(open(_SETTINGS_FILE, encoding='utf-8').read()) if _os.path.exists(_SETTINGS_FILE) else {}
                    bundle = _json.dumps({'workspaces': ws_data, 'settings': s_data}, ensure_ascii=False, indent=2)
                    if gist_id:
                        _gist_sync.update_gist(token, gist_id, bundle)
                        new_gist_id = gist_id
                    else:
                        new_gist_id = _gist_sync.create_gist(token, bundle)
                    return ('ok', new_gist_id)
                except Exception as e:
                    return ('error', str(e))

            result_holder = [None]

            def thread_run():
                result_holder[0] = run()
                QTimer.singleShot(0, on_upload_done)

            def on_upload_done():
                upload_btn.setEnabled(True)
                download_btn.setEnabled(True)
                result = result_holder[0]
                if result and result[0] == 'ok':
                    new_gist_id = result[1]
                    gist_id_edit.setText(new_gist_id)
                    save_token_and_gist(token, new_gist_id)
                    status_lbl.setStyleSheet('color:#a6e3a1; font-size:12px;')
                    status_lbl.setText(f'✅ Enviado com sucesso! Gist ID: {new_gist_id}')
                    ToastManager.show(self, 'Sincronizado com a nuvem!', 'success')
                else:
                    status_lbl.setStyleSheet('color:#f38ba8; font-size:12px;')
                    status_lbl.setText(f'❌ Erro: {result[1] if result else "Desconhecido"}')

            threading.Thread(target=thread_run, daemon=True).start()

        def on_download():
            from PySide6.QtWidgets import QMessageBox
            token = get_token()
            gist_id = get_gist_id()
            if not token or not gist_id:
                status_lbl.setStyleSheet('color:#f38ba8; font-size:12px;')
                status_lbl.setText('❌ Informe o token e o Gist ID.')
                return
            reply = QMessageBox.question(
                dlg, 'Confirmar download',
                'Isso substituirá suas configurações locais. Continuar?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            upload_btn.setEnabled(False)
            download_btn.setEnabled(False)
            status_lbl.setStyleSheet('color:#a6adc8; font-size:12px;')
            status_lbl.setText('Baixando...')

            result_holder = [None]

            def run():
                try:
                    content = _gist_sync.fetch_gist(token, gist_id)
                    import json as _j
                    bundle = _j.loads(content)
                    return ('ok', bundle)
                except Exception as e:
                    return ('error', str(e))

            def thread_run():
                result_holder[0] = run()
                QTimer.singleShot(0, on_download_done)

            def on_download_done():
                upload_btn.setEnabled(True)
                download_btn.setEnabled(True)
                result = result_holder[0]
                if result and result[0] == 'ok':
                    bundle = result[1]
                    try:
                        from .storage import _WORKSPACES_FILE, _SETTINGS_FILE
                        import json as _j
                        if 'workspaces' in bundle:
                            with open(_WORKSPACES_FILE, 'w', encoding='utf-8') as f:
                                _j.dump(bundle['workspaces'], f, ensure_ascii=False, indent=2)
                        if 'settings' in bundle:
                            with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                                _j.dump(bundle['settings'], f, ensure_ascii=False, indent=2)
                        save_token_and_gist(token, gist_id)
                        self._workspaces = load_workspaces()
                        self._active_workspace = self._workspaces[0]
                        self._services = self._active_workspace.services
                        self._active_service = None
                        self._active_account = None
                        self._rebuild_sidebar()
                        self._apply_theme(load_settings().get('theme', 'dark'))
                        status_lbl.setStyleSheet('color:#a6e3a1; font-size:12px;')
                        status_lbl.setText('✅ Configurações restauradas com sucesso!')
                        ToastManager.show(self, 'Configurações baixadas da nuvem!', 'success')
                    except Exception as e:
                        status_lbl.setStyleSheet('color:#f38ba8; font-size:12px;')
                        status_lbl.setText(f'❌ Erro ao aplicar: {e}')
                else:
                    status_lbl.setStyleSheet('color:#f38ba8; font-size:12px;')
                    status_lbl.setText(f'❌ Erro: {result[1] if result else "Desconhecido"}')

            threading.Thread(target=thread_run, daemon=True).start()

        upload_btn.clicked.connect(on_upload)
        download_btn.clicked.connect(on_download)
        dlg.exec()

    def _show_import_dialog(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                                        QHBoxLayout, QRadioButton, QButtonGroup,
                                        QFileDialog, QDialogButtonBox, QMessageBox)
        dlg = QDialog(self)
        dlg.setWindowTitle('📥 Importar do Rambox/Ferdium')
        dlg.setMinimumWidth(460)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel('📥 Importar configurações do Rambox ou Ferdium')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)

        layout.addWidget(QLabel('Selecione o arquivo de configuração do Rambox ou Ferdium:'))

        file_row = QHBoxLayout()
        file_lbl = QLabel('Nenhum arquivo selecionado')
        file_lbl.setStyleSheet('color:#6c7086; font-size:11px;')
        file_lbl.setWordWrap(True)
        file_btn = QPushButton('📂 Selecionar arquivo...')
        file_btn.setObjectName('secondaryButton')
        file_row.addWidget(file_lbl, 1)
        file_row.addWidget(file_btn)
        layout.addLayout(file_row)

        radio_row = QHBoxLayout()
        radio_row.addWidget(QLabel('Formato:'))
        rb_rambox = QRadioButton('Rambox')
        rb_rambox.setChecked(True)
        rb_ferdium = QRadioButton('Ferdium')
        btn_group = QButtonGroup(dlg)
        btn_group.addButton(rb_rambox)
        btn_group.addButton(rb_ferdium)
        radio_row.addWidget(rb_rambox)
        radio_row.addWidget(rb_ferdium)
        radio_row.addStretch()
        layout.addLayout(radio_row)

        selected_path = [None]

        def select_file():
            path, _ = QFileDialog.getOpenFileName(dlg, 'Selecionar arquivo', '', 'JSON (*.json)')
            if path:
                selected_path[0] = path
                file_lbl.setText(path)
                file_lbl.setStyleSheet('color:#cdd6f4; font-size:11px;')
                # Auto-detect format from content
                try:
                    import json as _j
                    data = _j.loads(open(path, encoding='utf-8').read())
                    if isinstance(data, list) or 'workspaces' in data:
                        rb_rambox.setChecked(True)
                    elif 'services' in data and any(
                        isinstance(s.get('recipe'), dict) for s in data.get('services', [])
                    ):
                        rb_ferdium.setChecked(True)
                except Exception:
                    pass

        file_btn.clicked.connect(select_file)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        btns.rejected.connect(dlg.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName('primaryButton')
            ok_btn.setText('Importar')

        def on_import():
            path = selected_path[0]
            if not path:
                QMessageBox.warning(dlg, 'Orbit', 'Selecione um arquivo JSON.')
                return
            try:
                if rb_rambox.isChecked():
                    ws = import_rambox(path)
                else:
                    ws = import_ferdium(path)
                if ws:
                    self._workspaces.append(ws)
                    self._switch_workspace(ws)
                    self._save()
                    dlg.accept()
                    n = len(ws.services)
                    ToastManager.show(self, f'{n} serviços importados com sucesso!', 'success')
            except Exception as e:
                QMessageBox.critical(dlg, 'Erro ao importar', str(e))
                ToastManager.show(self, f'Erro ao importar: {e}', 'error')

        btns.accepted.connect(on_import)
        layout.addWidget(btns)
        dlg.exec()

    def _show_stats_dialog(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QDialogButtonBox,
                                        QScrollArea, QWidget, QHBoxLayout, QProgressBar)
        weekly = get_weekly_totals()
        dlg = QDialog(self)
        dlg.setWindowTitle('Estatísticas de uso — últimos 7 dias')
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel('⏱ Tempo por serviço (últimos 7 dias)')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)
        if not weekly:
            layout.addWidget(QLabel('Nenhuma sessão registrada ainda.'))
        else:
            max_sec = weekly[0]['total'] if weekly else 1
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            container = QWidget()
            c_layout = QVBoxLayout(container)
            c_layout.setSpacing(8)
            for item in weekly:
                row = QWidget()
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(0, 0, 0, 0)
                lbl = QLabel(item['name'])
                lbl.setMinimumWidth(120)
                r_layout.addWidget(lbl)
                bar = QProgressBar()
                bar.setRange(0, int(max_sec))
                bar.setValue(int(item['total']))
                bar.setTextVisible(False)
                bar.setFixedHeight(12)
                bar.setStyleSheet(
                    'QProgressBar{border-radius:6px; background:#313244;}'
                    'QProgressBar::chunk{background:#cba6f7; border-radius:6px;}'
                )
                r_layout.addWidget(bar, 1)
                dur = QLabel(fmt_duration(item['total']))
                dur.setMinimumWidth(70)
                dur.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                r_layout.addWidget(dur)
                c_layout.addWidget(row)
            scroll.setWidget(container)
            layout.addWidget(scroll)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)
        dlg.exec()

    def _show_shortcuts_dialog(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                                        QDialogButtonBox, QLabel, QPushButton)
        from .storage import _DEFAULT_SHORTCUTS
        sc = load_shortcuts()
        ACTION_LABELS = {
            'focus_mode':   'Modo foco',
            'palette':      'Paleta de comandos',
            'zoom_in':      'Zoom +',
            'zoom_out':     'Zoom -',
            'zoom_reset':   'Zoom reset',
            'dnd_toggle':   'Não perturbe',
            'quick_switch': 'Quick switch',
        }
        dlg = QDialog(self)
        dlg.setWindowTitle('Atalhos de teclado')
        dlg.setMinimumWidth(380)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel('⌨ Atalhos de teclado')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)
        hint = QLabel('Clique no campo e pressione a combinação desejada.')
        hint.setStyleSheet('font-size:11px; color:#6c7086;')
        layout.addWidget(hint)
        form = QFormLayout()
        form.setSpacing(8)
        edits = {}
        for action, label in ACTION_LABELS.items():
            edit = QLineEdit(sc.get(action, ''))
            edit.setPlaceholderText('ex: Ctrl+Shift+F')
            edit.setReadOnly(True)

            def make_handler(e=edit):
                from PySide6.QtGui import QKeySequence
                def keyPressEvent(event):
                    key = event.key()
                    mods = event.modifiers()
                    if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
                        return
                    combo = QKeySequence(int(mods) | key).toString()
                    e.setText(combo)
                e.keyPressEvent = keyPressEvent

            make_handler()
            form.addRow(label, edit)
            edits[action] = edit
        layout.addLayout(form)
        reset_btn = QPushButton('↺ Restaurar padrões')
        reset_btn.setObjectName('secondaryButton')
        reset_btn.clicked.connect(lambda: [edits[a].setText(v) for a, v in _DEFAULT_SHORTCUTS.items()])
        layout.addWidget(reset_btn)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        btns.rejected.connect(dlg.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName('primaryButton')
            ok_btn.setText('Salvar')

        def on_accept():
            new_sc = {action: edit.text() for action, edit in edits.items()}
            save_shortcuts(new_sc)
            dlg.accept()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, 'Orbit',
                'Atalhos salvos! Reinicie o Orbit para aplicar as mudanças.')

        btns.accepted.connect(on_accept)
        layout.addWidget(btns)
        dlg.exec()

    def _setup_tray(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.ico')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        )
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip('Orbit')

        tray_menu = QMenu()
        show_act = tray_menu.addAction('Mostrar Orbit')
        show_act.triggered.connect(self._show_and_raise)
        tray_menu.addSeparator()
        lock_act = tray_menu.addAction('Bloquear agora')
        lock_act.setIcon(svg_icon('lock-closed', 14, '#6c7086'))
        lock_act.triggered.connect(self._lock_now)
        pin_act = tray_menu.addAction('Configurar PIN...')
        pin_act.setIcon(svg_icon('key', 14, '#6c7086'))
        pin_act.triggered.connect(self._show_pin_config_dialog)
        encrypt_act = tray_menu.addAction('Criptografar arquivos...')
        encrypt_act.setIcon(svg_icon('lock-closed', 14, '#6c7086'))
        encrypt_act.triggered.connect(self._show_encrypt_config_dialog)
        tray_menu.addSeparator()
        startup_act = tray_menu.addAction('Iniciar com o Windows')
        startup_act.setCheckable(True)
        startup_act.setChecked(self._is_startup_enabled())
        startup_act.triggered.connect(lambda checked: self._set_startup(checked))
        tray_menu.addSeparator()
        from PySide6.QtGui import QActionGroup
        theme_menu = tray_menu.addMenu('Tema')
        theme_group = QActionGroup(theme_menu)
        theme_group.setExclusive(True)
        for t_id, t_label, t_icon in [('dark', 'Escuro', 'moon'), ('light', 'Claro', 'sun'), ('system', 'Automático', 'computer-desktop')]:
            act = theme_menu.addAction(t_label)
            act.setIcon(svg_icon(t_icon, 14, '#6c7086'))
            act.setCheckable(True)
            act.setChecked(self._theme == t_id)
            act.triggered.connect(lambda _, t=t_id: self._apply_theme(t))
            theme_group.addAction(act)
        accent_menu = tray_menu.addMenu('🎨 Accent')
        for accent_name in ACCENTS:
            act = accent_menu.addAction(f'● {accent_name}')
            act.setCheckable(True)
            act.setChecked(accent_name == self._accent)
            act.triggered.connect(lambda checked, n=accent_name: self._set_accent(n))
        tray_menu.addSeparator()
        ad_block_act = tray_menu.addAction('Bloquear anúncios')
        ad_block_act.setIcon(svg_icon('shield-check', 14, '#6c7086'))
        ad_block_act.setCheckable(True)
        ad_block_act.setChecked(load_settings().get('ad_block', True))
        ad_block_act.triggered.connect(lambda checked: self._toggle_ad_block(checked))
        update_act = tray_menu.addAction('Verificar atualizações')
        update_act.setIcon(svg_icon('arrow-path', 14, '#6c7086'))
        update_act.triggered.connect(lambda: self._check_updates(silent=False))
        tray_menu.addSeparator()

        # DND submenu
        dnd_menu = tray_menu.addMenu('Não perturbe')
        dnd_menu.setIcon(svg_icon('bell-slash', 14, '#6c7086'))
        self._tray_dnd_menu = dnd_menu
        self._build_dnd_menu(dnd_menu)

        # Privacy mode
        self._tray_privacy_act = tray_menu.addAction('🕶️ Modo Privacidade')
        self._tray_privacy_act.setCheckable(True)
        self._tray_privacy_act.setChecked(self._privacy_mode)
        self._tray_privacy_act.triggered.connect(self._toggle_privacy_mode)

        tray_menu.addSeparator()
        stats_act = tray_menu.addAction('Estatísticas')
        stats_act.setIcon(svg_icon('chart-bar', 14, '#6c7086'))
        stats_act.triggered.connect(self._show_stats_dialog)
        shortcuts_act = tray_menu.addAction('Atalhos')
        shortcuts_act.setIcon(svg_icon('command-line', 14, '#6c7086'))
        shortcuts_act.triggered.connect(self._show_shortcuts_dialog)
        reading_list_act = tray_menu.addAction('📚 Lista de Leitura')
        reading_list_act.triggered.connect(self._show_reading_list)
        ws_schedule_act = tray_menu.addAction('⏰ Agendamento de Workspace')
        ws_schedule_act.triggered.connect(self._show_workspace_schedule)

        tray_menu.addSeparator()
        backup_menu = tray_menu.addMenu('Backup')
        backup_menu.setIcon(svg_icon('archive-box-arrow-down', 14, '#6c7086'))
        export_act = backup_menu.addAction('Exportar configurações')
        export_act.setIcon(svg_icon('arrow-up-tray', 14, '#6c7086'))
        export_act.triggered.connect(self._export_backup)
        import_act = backup_menu.addAction('Importar configurações')
        import_act.setIcon(svg_icon('arrow-down-tray', 14, '#6c7086'))
        import_act.triggered.connect(self._import_backup)
        cloud_act = tray_menu.addAction('Sincronização na nuvem...')
        cloud_act.setIcon(svg_icon('cloud-arrow-up', 14, '#6c7086'))
        cloud_act.triggered.connect(self._show_cloud_sync_dialog)
        rambox_act = tray_menu.addAction('Importar do Rambox/Ferdium...')
        rambox_act.setIcon(svg_icon('arrow-down-tray', 14, '#6c7086'))
        rambox_act.triggered.connect(self._show_import_dialog)

        tray_menu.addSeparator()
        quit_act = tray_menu.addAction('Fechar Orbit')
        quit_act.triggered.connect(QApplication.instance().quit)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(
            lambda reason: self._show_and_raise()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self._tray.show()

    def _show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_ad_block(self, enabled: bool):
        set_ad_block(enabled)
        settings = load_settings()
        settings['ad_block'] = enabled
        save_settings(settings)

    # ── DND ───────────────────────────────────────────────────────────────────

    def _is_dnd_active(self) -> bool:
        if self._dnd_until is not None and time.time() < self._dnd_until:
            return True
        return is_quiet_now(load_settings())

    def _set_dnd(self, minutes: Optional[int]):
        if minutes is None:
            self._dnd_until = None
        else:
            self._dnd_until = time.time() + minutes * 60
        self._update_dnd_ui()

    def _toggle_dnd_shortcut(self):
        if self._is_dnd_active():
            self._set_dnd(None)
        else:
            self._set_dnd(60)

    def _update_dnd_ui(self):
        if self._active_service:
            self._refresh_header()

    def _build_dnd_menu(self, menu: QMenu):
        menu.clear()
        if self._is_dnd_active():
            act = menu.addAction('Ativar notificações')
            act.setIcon(svg_icon('bell', 14, '#6c7086'))
            act.triggered.connect(lambda: self._set_dnd(None))
            menu.addSeparator()
        act15 = menu.addAction('15 minutos')
        act15.setIcon(svg_icon('bell-slash', 14, '#6c7086'))
        act15.triggered.connect(lambda: self._set_dnd(15))
        act60 = menu.addAction('1 hora')
        act60.setIcon(svg_icon('bell-slash', 14, '#6c7086'))
        act60.triggered.connect(lambda: self._set_dnd(60))
        act240 = menu.addAction('4 horas')
        act240.setIcon(svg_icon('bell-slash', 14, '#6c7086'))
        act240.triggered.connect(lambda: self._set_dnd(240))
        act_tom = menu.addAction('Até amanhã')
        act_tom.setIcon(svg_icon('bell-slash', 14, '#6c7086'))
        act_tom.triggered.connect(lambda: self._set_dnd(self._until_tomorrow_minutes()))
        menu.addSeparator()
        sched_act = menu.addAction('Agenda de silêncio...')
        sched_act.setIcon(svg_icon('clock', 14, '#6c7086'))
        sched_act.triggered.connect(self._show_quiet_hours_dialog)

    def _until_tomorrow_minutes(self) -> int:
        import datetime
        now = datetime.datetime.now()
        tomorrow = (now + datetime.timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        return max(1, int((tomorrow - now).total_seconds() / 60))

    def _show_dnd_menu(self):
        menu = QMenu(self)
        self._build_dnd_menu(menu)
        btn = self.sender()
        if btn:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        else:
            menu.exec(self.cursor().pos())

    def _show_quiet_hours_dialog(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                                        QTimeEdit, QDialogButtonBox, QLabel, QGroupBox,
                                        QGridLayout)
        from PySide6.QtCore import QTime
        settings = load_settings()
        qh = settings.get('quiet_hours', {})

        dlg = QDialog(self)
        dlg.setWindowTitle('Agenda de silêncio automático')
        dlg.setModal(True)
        dlg.setMinimumWidth(380)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel('⏰ Agenda de silêncio automático')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)

        enabled_cb = QCheckBox('Ativar agenda de silêncio automático')
        enabled_cb.setChecked(qh.get('enabled', False))
        layout.addWidget(enabled_cb)

        # Time range
        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.addWidget(QLabel('De:'))
        start_edit = QTimeEdit()
        start_edit.setDisplayFormat('HH:mm')
        sh, sm = map(int, qh.get('start', '22:00').split(':'))
        start_edit.setTime(QTime(sh, sm))
        time_layout.addWidget(start_edit)
        time_layout.addWidget(QLabel('Até:'))
        end_edit = QTimeEdit()
        end_edit.setDisplayFormat('HH:mm')
        eh, em = map(int, qh.get('end', '08:00').split(':'))
        end_edit.setTime(QTime(eh, em))
        time_layout.addWidget(end_edit)
        time_layout.addStretch()
        layout.addWidget(time_widget)

        # Day checkboxes
        days_group = QGroupBox('Dias da semana')
        days_layout = QHBoxLayout(days_group)
        day_labels = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        active_days = qh.get('days', [0, 1, 2, 3, 4])
        day_cbs = []
        for i, lbl in enumerate(day_labels):
            cb = QCheckBox(lbl)
            cb.setChecked(i in active_days)
            days_layout.addWidget(cb)
            day_cbs.append(cb)
        layout.addWidget(days_group)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        btns.rejected.connect(dlg.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName('primaryButton')
            ok_btn.setText('Salvar')

        def on_save():
            st = start_edit.time()
            et = end_edit.time()
            settings_now = load_settings()
            settings_now['quiet_hours'] = {
                'enabled': enabled_cb.isChecked(),
                'start': f'{st.hour():02d}:{st.minute():02d}',
                'end': f'{et.hour():02d}:{et.minute():02d}',
                'days': [i for i, cb in enumerate(day_cbs) if cb.isChecked()],
            }
            save_settings(settings_now)
            dlg.accept()

        btns.accepted.connect(on_save)
        layout.addWidget(btns)
        dlg.exec()

    def _show_notif_history_panel(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton
        # Reuse existing dialog if open
        if self._notif_history_dlg and self._notif_history_dlg.isVisible():
            self._notif_history_dlg.raise_()
            return

        dlg = QDialog(self)
        dlg.setWindowTitle('Histórico de notificações')
        dlg.setMinimumWidth(420)
        dlg.setMinimumHeight(400)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel('Histórico de notificações')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)

        lst = QListWidget()
        lst.setSpacing(2)
        history = get_history()
        if not history:
            lst.addItem('Nenhuma notificação registrada.')
        else:
            for entry in history:
                text = f'{entry.service_name} — {entry.title}\n{entry.timestamp[:19].replace("T", " ")}'
                item = QListWidgetItem(text)
                lst.addItem(item)
        layout.addWidget(lst, 1)

        clear_btn = QPushButton('Limpar histórico')
        clear_btn.setObjectName('secondaryButton')
        clear_btn.setCursor(Qt.PointingHandCursor)

        def on_clear():
            clear_history()
            lst.clear()
            lst.addItem('Nenhuma notificação registrada.')

        clear_btn.clicked.connect(on_clear)
        layout.addWidget(clear_btn)

        self._notif_history_dlg = dlg
        dlg.show()

    # ── quick switch ──────────────────────────────────────────────────────────

    def _quick_switch(self):
        if len(self._recent_services) < 2:
            return
        prev_id = self._recent_services[1]
        svc = next((s for s in self._services if s.id == prev_id), None)
        if svc:
            self._select_service(svc)

    def _select_service_by_id(self, svc_id: str):
        svc = next((s for s in self._services if s.id == svc_id), None)
        if svc:
            self._select_service(svc)

    # ── multi-window ──────────────────────────────────────────────────────────

    def _open_in_window(self, service: Service, account: Account):
        win = QWidget(None, Qt.Window)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.setWindowTitle(f'Orbit — {service.name} ({account.label})')
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.ico')
        if os.path.exists(icon_path):
            win.setWindowIcon(QIcon(icon_path))
        win.resize(1200, 800)
        layout = QVBoxLayout(win)
        layout.setContentsMargins(0, 0, 0, 0)
        view = ServiceView(
            account.profile_name,
            account.url,
            service_type=service.service_type,
            custom_css=service.custom_css,
            zoom=service.zoom,
        )
        layout.addWidget(view)
        win.show()
        self._detached_windows.append(win)
        win.destroyed.connect(
            lambda: self._detached_windows.remove(win) if win in self._detached_windows else None
        )

    # ── picture-in-picture ────────────────────────────────────────────────────

    def _open_pip(self, service: Service, account: Account):
        pip = QWidget(None, Qt.Window | Qt.WindowStaysOnTopHint)
        pip.setAttribute(Qt.WA_DeleteOnClose)
        pip.setWindowTitle(f'PiP — {service.name}')
        pip.resize(400, 300)
        pip.setMinimumSize(280, 200)
        screen = QApplication.primaryScreen().availableGeometry()
        pip.move(screen.right() - 420, screen.bottom() - 320)
        layout = QVBoxLayout(pip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title_bar = QWidget()
        title_bar.setFixedHeight(24)
        title_bar.setStyleSheet('background:#181825;')
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(8, 0, 4, 0)
        tb_lbl = QLabel(f'🐙 {service.name}')
        tb_lbl.setStyleSheet('color:#cdd6f4; font-size:11px;')
        tb_layout.addWidget(tb_lbl)
        tb_layout.addStretch()
        close_btn = QPushButton('✕')
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet('background:transparent; color:#6c7086; border:none; font-size:11px;')
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(pip.close)
        tb_layout.addWidget(close_btn)
        layout.addWidget(title_bar)
        view = ServiceView(
            account.profile_name,
            account.url,
            service_type=service.service_type,
            custom_css=service.custom_css,
            zoom=service.zoom,
        )
        layout.addWidget(view, 1)
        pip.show()
        self._pip_windows.append(pip)
        pip.destroyed.connect(
            lambda: self._pip_windows.remove(pip) if pip in self._pip_windows else None
        )

    # ── pop-out service window ────────────────────────────────────────────────

    def _popout_service(self, svc: Service):
        if not svc.accounts:
            ToastManager.show(self, 'Adicione uma conta antes de destacar', 'error')
            return
        acc = (self._active_account
               if (self._active_service and self._active_service.id == svc.id and self._active_account)
               else svc.accounts[0])
        win = QMainWindow()
        win.setWindowTitle(f'Orbit — {svc.name}')
        win.resize(1024, 768)
        key = (svc.id, acc.id)
        if key in self._views:
            # Can't reparent existing view — create a fresh one at the current URL
            view = ServiceView(
                acc.profile_name, acc.url,
                service_type=svc.service_type,
                custom_css=svc.custom_css,
                zoom=svc.zoom,
            )
            current_url = self._views[key].url()
            if current_url.isValid() and not current_url.isEmpty():
                view.load(current_url)
        else:
            view = ServiceView(
                acc.profile_name, acc.url,
                service_type=svc.service_type,
                custom_css=svc.custom_css,
                zoom=svc.zoom,
            )
        win.setCentralWidget(view)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.ico')
        if os.path.exists(icon_path):
            win.setWindowIcon(QIcon(icon_path))
        self._popout_windows.append(win)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.destroyed.connect(
            lambda: self._popout_windows.remove(win) if win in self._popout_windows else None
        )
        win.show()
        ToastManager.show(self, f'{svc.name} aberto em janela separada', 'success')

    # ── workspace schedule ────────────────────────────────────────────────────

    def _check_workspace_schedule(self):
        from .workspace_schedule import get_active_workspace_id
        ws_id = get_active_workspace_id(self._ws_schedule, self._workspaces)
        if ws_id and ws_id != self._active_workspace.id:
            target = next((w for w in self._workspaces if w.id == ws_id), None)
            if target:
                self._switch_workspace(target)
                ToastManager.show(self, f'Workspace trocado: {target.name}', 'info')

    def _show_workspace_schedule(self):
        from .workspace_schedule import load_schedule
        from .dialogs import WorkspaceScheduleDialog
        self._ws_schedule = load_schedule()
        dlg = WorkspaceScheduleDialog(self._workspaces, self._ws_schedule, self)
        if dlg.exec():
            self._ws_schedule = load_schedule()

    # ── reading list ──────────────────────────────────────────────────────────

    def _show_reading_list(self):
        from .reading_list import load_reading_list, mark_read, remove_item
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                                        QListWidgetItem, QPushButton, QLabel, QDialogButtonBox)

        items = load_reading_list()

        dlg = QDialog(self)
        dlg.setWindowTitle('📚 Lista de Leitura')
        dlg.setMinimumSize(560, 480)
        lay = QVBoxLayout(dlg)

        header = QLabel(f'📚 Lista de Leitura  ({len(items)} itens)')
        header.setStyleSheet('font-size: 15px; font-weight: bold; padding: 4px 0;')
        lay.addWidget(header)

        lst = QListWidget()
        for item in items:
            text = f"{'✅ ' if item.read else '🔵 '}{item.title[:60]}{'...' if len(item.title) > 60 else ''}"
            text += f"\n   {item.service_name}  •  {item.url[:60]}"
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, item)
            if item.read:
                it.setForeground(QColor('#585b70'))
            lst.addItem(it)
        lay.addWidget(lst)

        row = QHBoxLayout()
        open_btn = QPushButton('Abrir no Serviço')
        mark_btn = QPushButton('Marcar como Lido')
        del_btn = QPushButton('Remover')
        row.addWidget(open_btn)
        row.addWidget(mark_btn)
        row.addWidget(del_btn)
        row.addStretch()
        lay.addLayout(row)

        def _open():
            it = lst.currentItem()
            if it:
                import webbrowser
                webbrowser.open(it.data(Qt.UserRole).url)

        def _mark():
            it = lst.currentItem()
            if it:
                reading_item = it.data(Qt.UserRole)
                mark_read(reading_item.url)
                it.setForeground(QColor('#585b70'))
                old_text = it.text()
                if old_text.startswith('🔵 '):
                    it.setText('✅ ' + old_text[2:])

        def _remove():
            it = lst.currentItem()
            if it:
                remove_item(it.data(Qt.UserRole).url)
                lst.takeItem(lst.currentRow())

        open_btn.clicked.connect(_open)
        mark_btn.clicked.connect(_mark)
        del_btn.clicked.connect(_remove)

        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(dlg.accept)
        lay.addWidget(box)
        dlg.exec()

    # ── URL scheme registry ───────────────────────────────────────────────────

    def _register_url_scheme(self):
        """Register orbit:// URL scheme in Windows registry."""
        try:
            import winreg, sys
            exe = sys.executable
            key_path = r'Software\Classes\Orbit'
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'URL:Orbit Protocol')
                winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r'\shell\open\command') as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, f'"{exe}" "%1"')
        except Exception:
            pass  # Non-fatal

    def _check_updates(self, silent: bool = False):
        from .updater import check_for_update
        import threading

        def run():
            has_update, latest, url = check_for_update()
            if has_update:
                self._tray.showMessage(
                    'Orbit — Atualização disponível',
                    f'Versão {latest} disponível! Clique para baixar.',
                    QSystemTrayIcon.MessageIcon.Information,
                    8000,
                )

        t = threading.Thread(target=run, daemon=True)
        t.start()

    # ── lock screen ───────────────────────────────────────────────────────────

    def _init_encryption(self):
        """Prompt for master password at startup if encryption is enabled."""
        settings = load_settings()
        if not settings.get('encrypt_enabled'):
            return
        stored_hash = settings.get('encrypt_password_hash', '')
        from PySide6.QtWidgets import QMessageBox
        dlg = MasterPasswordDialog(mode='enter', parent=None)
        result = dlg.exec()
        if result == 2:  # "Forgot password" → wipe encrypted data
            from .storage import _WORKSPACES_FILE
            if os.path.exists(_WORKSPACES_FILE):
                os.remove(_WORKSPACES_FILE)
            s = load_settings()
            s.pop('encrypt_enabled', None)
            s.pop('encrypt_password_hash', None)
            save_settings(s)
            return
        if result != QDialog.DialogCode.Accepted:
            import sys
            sys.exit(0)
        pwd = dlg.password
        if not verify_password_hash(pwd, stored_hash):
            QMessageBox.critical(
                None,
                'Orbit',
                'Senha mestre incorreta. O aplicativo será encerrado.',
            )
            import sys
            sys.exit(1)
        set_session_password(pwd)

    def _show_encrypt_config_dialog(self):
        """Toggle file encryption on/off with the master password."""
        settings = load_settings()
        is_enabled = settings.get('encrypt_enabled', False)
        from .storage import _WORKSPACES_FILE

        if is_enabled:
            # Disable: verify current password then decrypt files
            dlg = MasterPasswordDialog(mode='enter', parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            pwd = dlg.password
            if not verify_password_hash(pwd, settings.get('encrypt_password_hash', '')):
                ToastManager.show(self, 'Senha incorreta.', 'error')
                return
            if os.path.exists(_WORKSPACES_FILE) and is_encrypted(_WORKSPACES_FILE):
                from .encryption import decrypt_file
                text = decrypt_file(_WORKSPACES_FILE, pwd)
                with open(_WORKSPACES_FILE, 'w', encoding='utf-8') as f:
                    f.write(text)
            settings.pop('encrypt_enabled', None)
            settings.pop('encrypt_password_hash', None)
            save_settings(settings)
            clear_session_password()
            ToastManager.show(self, 'Criptografia desativada.', 'success')
        else:
            # Enable: set new password and encrypt files
            dlg = MasterPasswordDialog(mode='set', parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            pwd = dlg.password
            if os.path.exists(_WORKSPACES_FILE) and not is_encrypted(_WORKSPACES_FILE):
                encrypt_file(_WORKSPACES_FILE, pwd)
            settings['encrypt_enabled'] = True
            settings['encrypt_password_hash'] = hash_password(pwd)
            save_settings(settings)
            set_session_password(pwd)
            ToastManager.show(self, '🔐 Criptografia ativada!', 'success')

    def _lock_now(self):
        settings = load_settings()
        pin_hash = settings.get('pin_hash')
        if not pin_hash:
            return
        if not self._lock_screen:
            self._lock_screen = LockScreen(pin_hash, self)
            self._lock_screen.unlocked.connect(self._lock_screen.hide)
        else:
            self._lock_screen._pin_hash = pin_hash
        self._lock_screen.reset()
        self._lock_screen.setGeometry(self.rect())
        self._lock_screen.show()
        self._lock_screen.raise_()

    def _show_shortcuts(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, QDialogButtonBox, QFrame
        dlg = QDialog(self)
        dlg.setWindowTitle('Atalhos de Teclado')
        dlg.setMinimumWidth(460)
        lay = QVBoxLayout(dlg)

        title = QLabel('⌨️  Atalhos do Orbit')
        title.setStyleSheet('font-size:16px; font-weight:bold; padding:8px 0;')
        lay.addWidget(title)

        shortcuts = [
            ('Ctrl+K', 'Command Palette'),
            ('Ctrl+Tab', 'Próximo serviço'),
            ('Ctrl+Shift+Tab', 'Serviço anterior'),
            ('Ctrl+1…9', 'Ir para serviço #N'),
            ('Ctrl+N', 'Novo serviço'),
            ('Ctrl+W', 'Fechar / desselecionar'),
            ('Ctrl+R', 'Recarregar serviço'),
            ('Ctrl+L', 'Tela de bloqueio'),
            ('Ctrl+M', 'Silenciar notificações'),
            ('Ctrl+B', 'Alternar sidebar compacta'),
            ('Ctrl+,', 'Configurações'),
            ('Ctrl+?', 'Este painel'),
            ('Ctrl+Shift+A', 'Painel IA'),
            ('Ctrl+Shift+P', 'Modo Privacidade'),
            ('Ctrl+Q', 'Sair'),
            ('F11', 'Tela cheia'),
        ]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)
        grid.setColumnMinimumWidth(0, 160)

        for row, (key, desc) in enumerate(shortcuts):
            key_lbl = QLabel(key)
            key_lbl.setStyleSheet('font-family: monospace; background: #313244; padding: 2px 8px; border-radius: 4px; color: #cdd6f4;')
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet('color: #a6adc8;')
            grid.addWidget(key_lbl, row, 0)
            grid.addWidget(desc_lbl, row, 1)

        scroll.setWidget(container)
        lay.addWidget(scroll)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.accept)
        lay.addWidget(btns)
        dlg.exec()

    def _check_auto_lock(self):
        settings = load_settings()
        minutes = settings.get('auto_lock_minutes', 0)
        if minutes <= 0 or not settings.get('pin_hash'):
            return
        if hasattr(self, '_lock_screen') and self._lock_screen and self._lock_screen.isVisible():
            return
        if time.time() - self._last_activity > minutes * 60:
            self._lock_now()
            self._last_activity = time.time()

    def _show_pin_config_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QSpinBox
        settings = load_settings()

        dlg = QDialog(self)
        dlg.setWindowTitle('Configurar PIN')
        dlg.setModal(True)
        dlg.setMinimumWidth(360)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel('🔐 Configurar PIN de bloqueio')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)

        hint = QLabel('Deixe em branco para remover o PIN.')
        hint.setStyleSheet('font-size:11px; color:#6c7086;')
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)

        new_pin = QLineEdit()
        new_pin.setPlaceholderText('Novo PIN (4 dígitos)')
        new_pin.setMaxLength(4)
        new_pin.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Novo PIN', new_pin)

        confirm_pin = QLineEdit()
        confirm_pin.setPlaceholderText('Confirmar PIN')
        confirm_pin.setMaxLength(4)
        confirm_pin.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Confirmar PIN', confirm_pin)

        auto_lock_spin = QSpinBox()
        auto_lock_spin.setRange(0, 120)
        auto_lock_spin.setValue(settings.get('auto_lock_minutes', 0))
        auto_lock_spin.setSuffix(' min (0 = desativado)')
        form.addRow('Bloqueio automático', auto_lock_spin)

        layout.addLayout(form)

        error_label = QLabel('')
        error_label.setStyleSheet('color:#f38ba8; font-size:12px;')
        layout.addWidget(error_label)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        btns.rejected.connect(dlg.reject)
        ok_btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setObjectName('primaryButton')
            ok_btn.setText('Salvar')

        def on_accept():
            p = new_pin.text().strip()
            c = confirm_pin.text().strip()
            s = load_settings()
            if p:
                if not p.isdigit() or len(p) != 4:
                    error_label.setText('O PIN deve ter exatamente 4 dígitos.')
                    return
                if p != c:
                    error_label.setText('Os PINs não correspondem.')
                    return
                s['pin_hash'] = hash_pin(p)
                if not self._lock_screen:
                    self._lock_screen = LockScreen(s['pin_hash'], self)
                    self._lock_screen.unlocked.connect(self._lock_screen.hide)
                else:
                    self._lock_screen._pin_hash = s['pin_hash']
            else:
                s.pop('pin_hash', None)
            s['auto_lock_minutes'] = auto_lock_spin.value()
            save_settings(s)
            dlg.accept()
            ToastManager.show(self, 'PIN configurado com sucesso!', 'success')

        btns.accepted.connect(on_accept)
        layout.addWidget(btns)
        new_pin.setFocus()
        dlg.exec()

    # ── onboarding ────────────────────────────────────────────────────────────

    def _show_onboarding(self):
        dlg = OnboardingDialog(self)
        dlg.theme_chosen.connect(self._apply_theme)
        dlg.service_chosen.connect(lambda st: self._quick_add_service(st))
        dlg.exec()
        s = load_settings()
        s['onboarding_done'] = True
        save_settings(s)

    def _quick_add_service(self, service_type: str):
        from .catalog import get_entry, GOOGLE_TYPES, google_url
        from .models import new_id, slugify
        entry = get_entry(service_type)
        if not entry:
            return
        svc_id = new_id(entry.type)
        acc_id = new_id('acc')
        profile_name = f'{entry.type}-{slugify(entry.name)}-{acc_id}'
        url = google_url(entry.type, 0) if entry.type in GOOGLE_TYPES else entry.default_url
        svc = Service(
            id=svc_id,
            service_type=entry.type,
            name=entry.name,
            icon=entry.icon,
            color=entry.color,
            accounts=[Account(id=acc_id, label=entry.name, url=url,
                              profile_name=profile_name, authuser=0)],
        )
        self._services.append(svc)
        self._rebuild_sidebar()
        self._select_service(svc)
        self._save()

    def closeEvent(self, event):
        g = self.geometry()
        settings = load_settings()
        settings['geometry'] = {'x': g.x(), 'y': g.y(), 'w': g.width(), 'h': g.height()}
        save_settings(settings)
        event.ignore()
        self.hide()
        self._tray.showMessage('Orbit', 'Rodando em segundo plano.', QSystemTrayIcon.MessageIcon.Information, 2000)

    # ── hibernate ─────────────────────────────────────────────────────────────

    def _setup_hibernate_timers(self):
        """Start/restart hibernate timer for all services that have it configured."""
        for svc in self._services:
            self._reset_hibernate_timer(svc)

    def _reset_hibernate_timer(self, service: Service):
        old = self._hibernate_timers.pop(service.id, None)
        if old:
            old.stop()
            old.deleteLater()
        if not service.hibernate_after:
            return
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(service.hibernate_after * 60 * 1000)
        timer.timeout.connect(lambda s=service: self._hibernate_service(s))
        timer.start()
        self._hibernate_timers[service.id] = timer

    def _hibernate_service(self, service: Service):
        """Pause all views for a service (load blank page to free memory)."""
        from PySide6.QtCore import QUrl
        for acc in service.accounts:
            key = (service.id, acc.id)
            if key in self._views:
                self._views[key].load(QUrl('about:blank'))
                self._hibernated.add(key)
        print(f'[hibernate] {service.name} hibernated')

    def _wake_service(self, service: Service, account: Account):
        """Wake a hibernated service by reloading its URL."""
        from PySide6.QtCore import QUrl
        key = (service.id, account.id)
        if key in self._hibernated:
            self._hibernated.discard(key)
            if key in self._views:
                self._views[key].load(QUrl(account.url))
        self._reset_hibernate_timer(service)

    # ── startup with Windows ──────────────────────────────────────────────────

    _STARTUP_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
    _STARTUP_NAME = 'Orbit'

    def _is_startup_enabled(self) -> bool:
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._STARTUP_KEY)
            winreg.QueryValueEx(key, self._STARTUP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _set_startup(self, enable: bool):
        import winreg, sys
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._STARTUP_KEY,
                                 0, winreg.KEY_SET_VALUE)
            if enable:
                exe = sys.executable
                script = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..', 'main.py'))
                winreg.SetValueEx(key, self._STARTUP_NAME, 0, winreg.REG_SZ,
                                  f'"{exe}" "{script}"')
            else:
                try:
                    winreg.DeleteValue(key, self._STARTUP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f'[startup] Error: {e}')

    # ── command palette ───────────────────────────────────────────────────────

    def _show_palette(self):
        from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QLabel
        from PySide6.QtCore import QTimer

        dlg = QDialog(self)
        dlg.setWindowTitle('Navegar')
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dlg.setModal(True)
        dlg.setMinimumWidth(460)
        dlg.setStyleSheet("""
            QDialog { background: #1e1e2e; border: 1px solid #45475a; border-radius: 12px; }
            QLineEdit { background: #181825; border: none; border-bottom: 1px solid #313244;
                        border-radius: 0; padding: 12px 16px; font-size: 15px; color: #cdd6f4; }
            QListWidget { background: #1e1e2e; border: none; padding: 4px; }
            QListWidget::item { padding: 8px 16px; border-radius: 6px; color: #cdd6f4; font-size: 13px; }
            QListWidget::item:selected { background: #313244; color: #cba6f7; }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        search = QLineEdit()
        search.setPlaceholderText('Buscar serviço ou conta…')
        layout.addWidget(search)

        lst = QListWidget()
        lst.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(lst)

        items = []
        for svc in self._services:
            items.append((f'{svc.name}', svc, None))
            for acc in svc.accounts:
                items.append((f'  {svc.name}  ›  {acc.label}', svc, acc))

        def _populate(query=''):
            lst.clear()
            q = query.lower()
            for label, svc, acc in items:
                if q in label.lower():
                    it = QListWidgetItem(label)
                    it.setData(Qt.UserRole, (svc, acc))
                    lst.addItem(it)
            if lst.count():
                lst.setCurrentRow(0)

        def _activate(item):
            data = item.data(Qt.UserRole)
            if data:
                svc, acc = data
                self._select_service(svc)
                if acc:
                    self._select_account(acc)
            dlg.accept()

        search.textChanged.connect(_populate)
        lst.itemActivated.connect(_activate)
        lst.itemDoubleClicked.connect(_activate)

        def _on_key(event):
            from PySide6.QtCore import Qt as _Qt
            if event.key() == _Qt.Key_Down:
                row = lst.currentRow()
                if row < lst.count() - 1:
                    lst.setCurrentRow(row + 1)
            elif event.key() == _Qt.Key_Up:
                row = lst.currentRow()
                if row > 0:
                    lst.setCurrentRow(row - 1)
            elif event.key() in (_Qt.Key_Return, _Qt.Key_Enter):
                item = lst.currentItem()
                if item:
                    _activate(item)
            elif event.key() == _Qt.Key_Escape:
                dlg.reject()
            else:
                QLineEdit.keyPressEvent(search, event)

        search.keyPressEvent = _on_key
        _populate()
        dlg.exec()

    # ── drag & drop sidebar reordering ────────────────────────────────────────

    def _svc_drag_enter(self, event):
        if event.mimeData().hasFormat('application/x-orbit-service'):
            event.acceptProposedAction()

    def _svc_drop(self, event):
        if not event.mimeData().hasFormat('application/x-orbit-service'):
            return
        svc_id = event.mimeData().data('application/x-orbit-service').toStdString()
        dragged = next((s for s in self._services if s.id == svc_id), None)
        if not dragged:
            return
        drop_y = event.position().toPoint().y()
        target_idx = len(self._services) - 1
        for i, svc in enumerate(self._services):
            btn = self._svc_btns.get(svc.id)
            if btn:
                btn_center_y = btn.mapTo(self._svc_container, btn.rect().center()).y()
                if drop_y < btn_center_y:
                    target_idx = i
                    break
        self._services.remove(dragged)
        target_idx = min(target_idx, len(self._services))
        self._services.insert(target_idx, dragged)
        self._rebuild_sidebar()
        self._save()
        event.acceptProposedAction()

    def handle_url_scheme(self, url: str):
        """Handle an orbit:// URL passed via command-line or protocol activation.

        Supported URLs:
          orbit://open                  — bring window to front
          orbit://service/<service_id>  — switch to a service by ID
          orbit://workspace/<name>      — switch to a workspace by name
        """
        self.show()
        self.raise_()
        self.activateWindow()

        try:
            path = url[len('orbit://'):]
            parts = [p for p in path.split('/') if p]
            if not parts:
                return
            command = parts[0].lower()
            if command == 'service' and len(parts) >= 2:
                service_id = parts[1]
                for svc in self._services:
                    if svc.id == service_id or svc.name.lower() == service_id.lower():
                        self._select_service(svc)
                        break
            elif command == 'workspace' and len(parts) >= 2:
                ws_name = parts[1].lower()
                for ws in self._workspaces:
                    if ws.name.lower() == ws_name:
                        self._switch_workspace(ws)
                        break
        except Exception:
            pass

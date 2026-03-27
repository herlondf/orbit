from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QPoint, QSize, QEvent, QRect, QUrl, Signal, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QContextMenuEvent,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QKeySequence,
)


def _orbit_logo_pixmap(size: int) -> QPixmap:
    """Render the Orbit SVG icon to a QPixmap of the given square size."""
    svg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.svg')
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    if os.path.exists(svg_path):
        from PySide6.QtCore import QByteArray
        renderer = QSvgRenderer(QByteArray(open(svg_path, 'rb').read()))
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        renderer.render(p, QRect(0, 0, size, size))
        p.end()
    return px
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStyledItemDelegate,
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
    hash_password,
    is_encrypted,
    set_session_password,
    verify_password_hash,
)
from .models import Account, Service, ServiceGroup, Workspace
from .storage import load_settings, save_settings, load_workspaces, save_workspaces, load_shortcuts, save_shortcuts
from .theme import get_tokens, ACCENTS
from . import gist_sync as _gist_sync
from .importer import import_rambox, import_ferdium
from .webview import ServiceView, _GOOGLE_TYPES, set_ad_block
from .stats import record_session, get_weekly_totals, fmt_duration
from .icons import IconFetcher, get_cached_pixmap, icon as svg_icon
from .sounds import play_sound
from .notif_history import load_history, add_notification, get_history, clear_history
from .service_status import ServiceStatusChecker
from .security_monitor import SecurityMonitor
from .taskbar import update_badge
from .notif_center import NotificationCenter
from .quiet_hours import is_quiet_now
from .dashboard import DashboardWidget
from .lock_screen import LockScreen, hash_pin
from .onboarding import OnboardingDialog
from .hover_effect import apply_hover_effect
from .toast import ToastManager
from .lottie_widget import LottieLabel
from .focus_profiles import (
    PROFILE_LABELS as _PROFILE_LABELS,
    PROFILE_ORDER as _PROFILE_ORDER,
    get_active_profile as _get_focus_profile,
    set_active_profile as _set_focus_profile,
    cycle_profile as _cycle_focus_profile,
    is_service_muted_by_profile as _svc_muted_by_profile,
    is_dnd_in_profile as _dnd_in_profile,
    load_profile_from_settings as _load_focus_profile,
    save_profile_to_settings as _save_focus_profile,
)
from .audit_log import log_event as _log_event
from .i18n import t as _t

# ── Splash progress hook — set by main.py before creating OrbitWindow ─────────
# Calling this triggers a processEvents() so the animated splash keeps moving.
_splash_tick: 'Optional[callable]' = None

def _tick() -> None:
    if _splash_tick is not None:
        _splash_tick()

# ── Theme system (delegates to app/theme.py) ─────────────────────────────────
# ── Custom sidebar button ──────────────────────────────────────────────────────

# ── Sidebar service data roles ─────────────────────────────────────────────────
_ROLE_SVC    = Qt.UserRole
_ROLE_BADGE  = Qt.UserRole + 1
_ROLE_STATUS = Qt.UserRole + 2
_ROLE_PIXMAP = Qt.UserRole + 3
_ROLE_SEP    = Qt.UserRole + 4   # group-header text (str) or None

_STATUS_COLORS = {
    'loading': '#fab387',
    'ready':   '#a6e3a1',
    'error':   '#f38ba8',
    'online':  '#a6e3a1',
    'slow':    '#f9e2af',
    'offline': '#f38ba8',
}


class ServiceDelegate(QStyledItemDelegate):  # pragma: no cover
    """
    Renders each service row inside the sidebar QListWidget.
    Eliminates the paintEvent-per-widget approach that caused vertical clipping.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.compact: bool = True
        self.accent: str = '#cba6f7'
        self.style: str = 'discord'  # 'discord' | 'arc' | 'dock' | 'notion'
        # Active bar animation: animates width 0→3 when item selected
        self._bar_width: float = 3.0
        self._bar_anim = QPropertyAnimation(self, b'bar_width')
        self._bar_anim.setDuration(200)
        self._bar_anim.setEasingCurve(QEasingCurve.OutCubic)
        # Hover float animation: sine-wave oscillation while cursor is over a row
        self._hover_offsets: dict[int, float] = {}
        self._hover_phases: dict[int, float] = {}
        self._hover_row: int = -1
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(16)  # ~60 fps
        self._hover_timer.timeout.connect(self._tick_hover)

    def _get_bar_width(self) -> float:
        return self._bar_width

    def _set_bar_width(self, v: float):
        self._bar_width = v
        if self.parent():
            self.parent().viewport().update()

    bar_width = Property(float, _get_bar_width, _set_bar_width)

    def animate_selection(self):
        """Trigger the accent bar width animation (call when selection changes)."""
        self._bar_anim.stop()
        self._bar_anim.setStartValue(0.0)
        self._bar_anim.setEndValue(3.0)
        self._bar_anim.start()

    def set_hovered_row(self, row: int) -> None:
        """Called by the parent list when mouse moves over a row."""
        self._hover_row = row
        if row >= 0 and not self._hover_timer.isActive():
            self._hover_timer.start()

    def _tick_hover(self) -> None:
        """Oscillate icon Y with a sine wave while hovered; decay smoothly on leave."""
        import math
        from PySide6.QtGui import QCursor
        lw = self.parent()
        if lw:
            pos = lw.viewport().mapFromGlobal(QCursor.pos())
            item = lw.itemAt(pos)
            self._hover_row = lw.row(item) if item else -1

        rows_to_process = set(self._hover_phases.keys())
        if self._hover_row >= 0:
            rows_to_process.add(self._hover_row)

        changed = False
        for row in list(rows_to_process):
            if row == self._hover_row:
                # Advance sine phase — 0.10 rad/tick ≈ ~1 cycle/sec at 60 fps
                phase = self._hover_phases.get(row, 0.0) + 0.10
                self._hover_phases[row] = phase
                self._hover_offsets[row] = math.sin(phase) * 4.0  # ±4 px
                changed = True
            else:
                # Smooth exponential decay back to 0
                current = self._hover_offsets.get(row, 0.0)
                if abs(current) < 0.15:
                    self._hover_offsets.pop(row, None)
                    self._hover_phases.pop(row, None)
                else:
                    self._hover_offsets[row] = current * 0.80
                    changed = True

        if (changed or self._hover_offsets) and lw:
            lw.viewport().update()
        elif not self._hover_offsets and self._hover_row < 0:
            self._hover_timer.stop()

    # ── Size hints per style ──────────────────────────────────────────────────
    _SIZES = {
        'discord':  {'compact': (56, 56), 'expanded': (200, 48)},
        'arc':      {'compact': (72, 64), 'expanded': (220, 48)},
        'dock':     {'compact': (64, 70), 'expanded': (220, 54)},
        'notion':   {'compact': (68, 48), 'expanded': (240, 36)},
        'slack':    {'compact': (60, 52), 'expanded': (220, 44)},
        'spotify':  {'compact': (58, 58), 'expanded': (210, 50)},
        'teams':    {'compact': (62, 56), 'expanded': (220, 48)},
        'telegram': {'compact': (60, 60), 'expanded': (210, 50)},
        'figma':    {'compact': (54, 54), 'expanded': (200, 42)},
        'linear':   {'compact': (56, 52), 'expanded': (210, 44)},
    }

    def sizeHint(self, option, index) -> QSize:
        if index.data(_ROLE_SEP) is not None:
            return QSize(option.rect.width() if option.rect.isValid() else 220, 26)
        sizes = self._SIZES.get(self.style, self._SIZES['discord'])
        w, h = sizes['compact'] if self.compact else sizes['expanded']
        return QSize(w, h)

    # ── Paint dispatcher ──────────────────────────────────────────────────────
    def paint(self, painter, option, index):  # noqa: C901
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        sep_text = index.data(_ROLE_SEP)
        if sep_text is not None:
            painter.setPen(QPen(QColor('#6c7086')))
            painter.setFont(QFont('Inter', 8, QFont.Bold))
            painter.drawText(option.rect.adjusted(10, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, str(sep_text).upper())
            painter.restore()
            return

        svc = index.data(_ROLE_SVC)
        if not svc:
            painter.restore()
            return

        from PySide6.QtWidgets import QStyle
        r = option.rect
        ctx = {
            'w': r.width(), 'h': r.height(), 'x0': r.x(), 'y0': r.y(),
            'is_selected': bool(option.state & QStyle.State_Selected),
            'is_hovered': bool(option.state & QStyle.State_MouseOver),
            'is_disabled': not getattr(svc, 'enabled', True),
            'badge': index.data(_ROLE_BADGE) or 0,
            'status': index.data(_ROLE_STATUS) or '',
            'pixmap': index.data(_ROLE_PIXMAP),
            'row': index.row(),
        }
        if ctx['is_disabled']:
            painter.setOpacity(0.4)

        style_fn = {
            'discord': self._paint_discord,
            'arc': self._paint_arc,
            'dock': self._paint_dock,
            'notion': self._paint_notion,
            'slack': self._paint_slack,
            'spotify': self._paint_spotify,
            'teams': self._paint_teams,
            'telegram': self._paint_telegram,
            'figma': self._paint_figma,
            'linear': self._paint_linear,
        }.get(self.style, self._paint_discord)
        style_fn(painter, svc, ctx)
        painter.restore()

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _draw_icon(self, painter, svc, pixmap, ix, iy, icon_size, radius, content_size=26):
        painter.setBrush(QBrush(QColor(svc.color)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(ix, iy, icon_size, icon_size, radius, radius)
        if pixmap and not pixmap.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            s = pixmap.scaled(content_size, content_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(ix + (icon_size - s.width()) // 2, iy + (icon_size - s.height()) // 2, s)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 230)))
            fs = max(8, content_size // 2)
            painter.setFont(QFont('Segoe UI', fs, QFont.Bold))
            painter.drawText(ix, iy, icon_size, icon_size, Qt.AlignCenter, svc.icon)

    def _draw_circular_icon(self, painter, svc, pixmap, ix, iy, icon_size, content_size=28):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addEllipse(float(ix), float(iy), float(icon_size), float(icon_size))
        painter.setClipPath(path)
        painter.setBrush(QBrush(QColor(svc.color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(ix, iy, icon_size, icon_size)
        if pixmap and not pixmap.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            s = pixmap.scaled(content_size, content_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(ix + (icon_size - s.width()) // 2, iy + (icon_size - s.height()) // 2, s)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 230)))
            fs = max(8, content_size // 2)
            painter.setFont(QFont('Segoe UI', fs, QFont.Bold))
            painter.drawText(ix, iy, icon_size, icon_size, Qt.AlignCenter, svc.icon)
        painter.setClipping(False)

    def _draw_badge(self, painter, badge, bx, by, style='pill'):
        if badge <= 0:
            return
        if style == 'dot':
            painter.setBrush(QBrush(QColor('#f38ba8')))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(bx, by, 10, 10)
        else:
            badge_text = str(badge) if badge <= 99 else '99+'
            badge_w = max(18, len(badge_text) * 7 + 6)
            painter.setBrush(QBrush(QColor('#f38ba8')))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bx, by, badge_w, 16, 8, 8)
            painter.setPen(QPen(QColor('#1e1e2e')))
            painter.setFont(QFont('Segoe UI', 8, QFont.Bold))
            painter.drawText(bx, by, badge_w, 16, Qt.AlignCenter, badge_text)

    def _draw_status_dot(self, painter, status, dx, dy):
        dot_color = _STATUS_COLORS.get(status)
        if dot_color:
            painter.setBrush(QBrush(QColor('#ffffff')))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(dx - 1, dy - 1, 10, 10)
            painter.setBrush(QBrush(QColor(dot_color)))
            painter.drawEllipse(dx, dy, 8, 8)

    def _draw_incognito(self, painter, svc, ix, iy):
        if getattr(svc, 'incognito', False):
            painter.setPen(QPen(QColor('#cdd6f4')))
            painter.setFont(QFont('Segoe UI Emoji', 9))
            painter.drawText(ix - 2, iy - 2, 14, 14, Qt.AlignCenter, '🕵')

    def _draw_name(self, painter, name, tx, ty, tw, th, color='#cdd6f4', size=10):
        painter.setPen(QPen(QColor(color)))
        font = QFont('Inter', size, QFont.Medium)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0.2)
        painter.setFont(font)
        fm = painter.fontMetrics()
        elided = fm.elidedText(name, Qt.ElideRight, tw)
        painter.drawText(tx, ty, tw, th, Qt.AlignVCenter | Qt.AlignLeft, elided)

    # ── DISCORD STYLE ─────────────────────────────────────────────────────────
    def _paint_discord(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 44
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Selection: pill accent on left edge
        if c['is_selected']:
            pill_h = int(h * 0.6)
            pill_y = y0 + (h - pill_h) // 2
            painter.setBrush(QBrush(QColor(self.accent)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0, pill_y, 4, pill_h, 2, 2)
            # Subtle bg glow
            painter.setBrush(QBrush(QColor(203, 166, 247, 20)))
            painter.drawRoundedRect(x0 + 6, y0 + 2, w - 10, h - 4, 12, 12)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 6, y0 + 2, w - 10, h - 4, 12, 12)

        # Circular icon
        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 10
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_circular_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 28)

        # Name (expanded)
        if not self.compact:
            self._draw_name(painter, svc.name, ix + icon_size + 10, y0, w - ix - icon_size - 30, h)

        # Badge: dot in compact, pill in expanded
        if c['badge'] > 0:
            if self.compact:
                self._draw_badge(painter, c['badge'], ix + icon_size - 10, iy - 2, 'dot')
            else:
                bx = x0 + w - 38
                self._draw_badge(painter, c['badge'], bx, y0 + (h - 16) // 2)

        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)
        self._draw_incognito(painter, svc, ix, iy)

    # ── ARC STYLE ─────────────────────────────────────────────────────────────
    def _paint_arc(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 36
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))
        margin = 6

        # Selection: full-width pill with accent tint
        if c['is_selected']:
            ac = QColor(self.accent)
            ac.setAlpha(25)
            painter.setBrush(QBrush(ac))
            painter.setPen(QPen(QColor(self.accent + '30'), 1))
            painter.drawRoundedRect(x0 + margin, y0 + 3, w - margin * 2, h - 6, 10, 10)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
            painter.drawRoundedRect(x0 + margin, y0 + 3, w - margin * 2, h - 6, 10, 10)

        # Rounded square icon
        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + margin + 8
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 12, 22)

        # Name (expanded)
        if not self.compact:
            self._draw_name(painter, svc.name, ix + icon_size + 10, y0, w - ix - icon_size - 30, h, size=11)

        # Badge: accent pill
        if c['badge'] > 0:
            if self.compact:
                self._draw_badge(painter, c['badge'], ix + icon_size - 10, iy - 4)
            else:
                badge_text = str(c['badge']) if c['badge'] <= 99 else '99+'
                badge_w = max(20, len(badge_text) * 7 + 8)
                bx = x0 + w - badge_w - margin - 6
                by = y0 + (h - 18) // 2
                ac = QColor(self.accent)
                ac.setAlpha(180)
                painter.setBrush(QBrush(ac))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(bx, by, badge_w, 18, 9, 9)
                painter.setPen(QPen(QColor('#ffffff')))
                painter.setFont(QFont('Segoe UI', 8, QFont.Bold))
                painter.drawText(bx, by, badge_w, 18, Qt.AlignCenter, badge_text)

        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)
        self._draw_incognito(painter, svc, ix, iy)

    # ── DOCK STYLE ────────────────────────────────────────────────────────────
    def _paint_dock(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        base_size = 42
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Magnification: grow icon when hovered
        is_hover_target = (c['row'] == self._hover_row)
        mag = min(1.0, abs(self._hover_offsets.get(c['row'], 0.0)) / 4.0 + 0.3) if is_hover_target else 0.0
        icon_size = int(base_size + 10 * mag) if is_hover_target else base_size

        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 12
        iy = y0 + (h - icon_size) // 2 + hover_off

        # Subtle reflection below icon
        if self.compact:
            ref_y = iy + icon_size + 2
            painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(ix + 4, ref_y, icon_size - 8, 2, 1, 1)

        # Icon
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 10, int(icon_size * 0.62))

        # Selection: dot below icon
        if c['is_selected']:
            dot_size = 6
            dx = x0 + (w - dot_size) // 2 if self.compact else ix + icon_size // 2 - dot_size // 2
            dy = iy + icon_size + 4
            painter.setBrush(QBrush(QColor(self.accent)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(dx, dy, dot_size, dot_size)

        # Name (expanded)
        if not self.compact:
            self._draw_name(painter, svc.name, ix + icon_size + 10, y0, w - ix - icon_size - 30, h)

        # Badge
        if c['badge'] > 0:
            self._draw_badge(painter, c['badge'], ix + icon_size - 12, iy - 4)

        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)
        self._draw_incognito(painter, svc, ix, iy)

    # ── NOTION STYLE ──────────────────────────────────────────────────────────
    def _paint_notion(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']

        # Selection: accent bar + surface bg
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x0, y0, w, h)
            painter.setBrush(QBrush(QColor(self.accent)))
            painter.drawRoundedRect(x0 + 2, y0 + 6, 3, h - 12, 2, 2)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 6)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x0, y0, w, h)

        if self.compact:
            # Compact: small square icon
            icon_size = 28
            ix = x0 + (w - icon_size) // 2
            iy = y0 + (h - icon_size) // 2
            self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 6, 18)
            if c['badge'] > 0:
                self._draw_badge(painter, c['badge'], ix + icon_size - 8, iy - 4, 'dot')
        else:
            # Expanded: color dot + text name + badge count right-aligned
            dot_size = 8
            dx = x0 + 14
            dy = y0 + (h - dot_size) // 2
            painter.setBrush(QBrush(QColor(svc.color)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(dx, dy, dot_size, dot_size)

            # Name
            tx = dx + dot_size + 10
            avail = w - tx - 40
            painter.setPen(QPen(QColor('#cdd6f4' if c['is_selected'] else '#a6adc8')))
            font = QFont('Inter', 11)
            painter.setFont(font)
            fm = painter.fontMetrics()
            elided = fm.elidedText(svc.name, Qt.ElideRight, avail)
            painter.drawText(tx, y0, avail, h, Qt.AlignVCenter | Qt.AlignLeft, elided)

            # Badge count right-aligned
            if c['badge'] > 0:
                badge_text = str(c['badge']) if c['badge'] <= 99 else '99+'
                painter.setPen(QPen(QColor(self.accent)))
                painter.setFont(QFont('JetBrains Mono, Consolas, monospace', 9, QFont.Bold))
                painter.drawText(x0 + w - 36, y0, 28, h, Qt.AlignVCenter | Qt.AlignRight, badge_text)

        self._draw_status_dot(painter, c['status'], x0 + w - 14 if not self.compact else x0 + (w + 28) // 2 - 2, y0 + h - 12 if not self.compact else y0 + (h + 28) // 2 - 2)

    # ── SLACK STYLE ───────────────────────────────────────────────────────────
    def _paint_slack(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 34
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Selection: left border 3px + bg tint
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 14)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x0, y0, w, h)
            painter.setBrush(QBrush(QColor(self.accent)))
            painter.drawRect(x0, y0 + 4, 3, h - 8)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x0, y0, w, h)

        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 12
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 8, 20)

        if not self.compact:
            self._draw_name(painter, svc.name, ix + icon_size + 8, y0, w - ix - icon_size - 28, h, '#d1d2d3', 10)
            if c['badge'] > 0:
                self._draw_badge(painter, c['badge'], x0 + w - 32, y0 + (h - 16) // 2)
        elif c['badge'] > 0:
            self._draw_badge(painter, c['badge'], ix + icon_size - 10, iy - 4, 'dot')
        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)

    # ── SPOTIFY STYLE ─────────────────────────────────────────────────────────
    def _paint_spotify(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 42
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Selection: rounded pill with green-tinted bg
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(29, 185, 84, 25)))  # Spotify green tint
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 4, y0 + 3, w - 8, h - 6, 6, 6)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 4, y0 + 3, w - 8, h - 6, 6, 6)

        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 8
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 6, 26)

        if not self.compact:
            name_c = '#1db954' if c['is_selected'] else '#b3b3b3'
            self._draw_name(painter, svc.name, ix + icon_size + 10, y0, w - ix - icon_size - 30, h, name_c, 11)
        if c['badge'] > 0:
            # Green dot badge (Spotify-like)
            bx = ix + icon_size - 8 if self.compact else x0 + w - 24
            by = iy - 2 if self.compact else y0 + (h - 8) // 2
            painter.setBrush(QBrush(QColor('#1db954')))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(bx, by, 8, 8)
        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)

    # ── TEAMS STYLE ───────────────────────────────────────────────────────────
    def _paint_teams(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 36
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Selection: blue left bar + light bg (corporate)
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(98, 100, 167, 30)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x0, y0, w, h)
            painter.setBrush(QBrush(QColor('#6264a7')))
            painter.drawRect(x0, y0, 4, h)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x0, y0, w, h)

        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 14
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 4, 22)  # low radius = square-ish

        if not self.compact:
            self._draw_name(painter, svc.name, ix + icon_size + 10, y0, w - ix - icon_size - 30, h, '#c5c6cb', 10)
            if c['badge'] > 0:
                self._draw_badge(painter, c['badge'], x0 + w - 34, y0 + (h - 16) // 2)
        elif c['badge'] > 0:
            self._draw_badge(painter, c['badge'], ix + icon_size - 10, iy - 4)
        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)

    # ── TELEGRAM STYLE ────────────────────────────────────────────────────────
    def _paint_telegram(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 42
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Hover/selection: subtle rounded bg
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(42, 141, 197, 30)))  # Telegram blue tint
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 4, y0 + 2, w - 8, h - 4, 10, 10)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 4, y0 + 2, w - 8, h - 4, 10, 10)

        # Circular avatar
        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 10
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_circular_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 26)

        if not self.compact:
            self._draw_name(painter, svc.name, ix + icon_size + 10, y0, w - ix - icon_size - 30, h, '#e4ecf0', 11)
        if c['badge'] > 0:
            bx = ix + icon_size - 12 if self.compact else x0 + w - 34
            by = iy - 2 if self.compact else y0 + (h - 16) // 2
            # Telegram blue badge
            badge_text = str(c['badge']) if c['badge'] <= 99 else '99+'
            badge_w = max(18, len(badge_text) * 7 + 6)
            painter.setBrush(QBrush(QColor('#2a8dc5')))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bx, by, badge_w, 16, 8, 8)
            painter.setPen(QPen(QColor('#ffffff')))
            painter.setFont(QFont('Segoe UI', 8, QFont.Bold))
            painter.drawText(bx, by, badge_w, 16, Qt.AlignCenter, badge_text)
        self._draw_status_dot(painter, c['status'], ix + icon_size - 8, iy + icon_size - 8)

    # ── FIGMA STYLE ───────────────────────────────────────────────────────────
    def _paint_figma(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 32
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Ultra-minimal: thin left line on selection, no bg
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(self.accent)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 1, y0 + 8, 2, h - 16, 1, 1)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 6)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 4, y0 + 2, w - 8, h - 4, 6, 6)

        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 12
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 8, 20)

        if not self.compact:
            color = '#e5e5e5' if c['is_selected'] else '#999'
            self._draw_name(painter, svc.name, ix + icon_size + 8, y0, w - ix - icon_size - 24, h, color, 10)
        if c['badge'] > 0:
            self._draw_badge(painter, c['badge'], ix + icon_size - 8, iy - 4, 'dot')
        self._draw_status_dot(painter, c['status'], ix + icon_size - 6, iy + icon_size - 6)

    # ── LINEAR STYLE ──────────────────────────────────────────────────────────
    def _paint_linear(self, painter, svc, c):
        x0, y0, w, h = c['x0'], c['y0'], c['w'], c['h']
        icon_size = 30
        hover_off = int(self._hover_offsets.get(c['row'], 0.0))

        # Selection: full-width subtle bg + left accent dot
        if c['is_selected']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 3, y0 + 2, w - 6, h - 4, 8, 8)
            painter.setBrush(QBrush(QColor(self.accent)))
            painter.drawEllipse(x0 + 4, y0 + (h - 6) // 2, 6, 6)
        elif c['is_hovered']:
            painter.setBrush(QBrush(QColor(255, 255, 255, 5)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0 + 3, y0 + 2, w - 6, h - 4, 8, 8)

        ix = x0 + (w - icon_size) // 2 if self.compact else x0 + 16
        iy = y0 + (h - icon_size) // 2 + hover_off
        self._draw_icon(painter, svc, c['pixmap'], ix, iy, icon_size, 7, 18)

        if not self.compact:
            color = '#f7f8f8' if c['is_selected'] else '#8a8f98'
            self._draw_name(painter, svc.name, ix + icon_size + 8, y0, w - ix - icon_size - 28, h, color, 10)
            if c['badge'] > 0:
                badge_text = str(c['badge']) if c['badge'] <= 99 else '99+'
                painter.setPen(QPen(QColor('#5e6ad2')))  # Linear purple
                painter.setFont(QFont('Inter', 9, QFont.Bold))
                painter.drawText(x0 + w - 32, y0, 24, h, Qt.AlignVCenter | Qt.AlignRight, badge_text)
        elif c['badge'] > 0:
            self._draw_badge(painter, c['badge'], ix + icon_size - 8, iy - 4, 'dot')
        self._draw_status_dot(painter, c['status'], ix + icon_size - 6, iy + icon_size - 6)


# ── Small inline icon label (header) ──────────────────────────────────────────

class _IconLabel(QWidget):  # pragma: no cover
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

class _RichTooltip(QWidget):  # pragma: no cover
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
        from PySide6.QtCore import QRect
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

class _StatusBadge(QWidget):  # pragma: no cover
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



# ── In-app Toast Notification ─────────────────────────────────────────────────

class _ToastNotification(QWidget):  # pragma: no cover
    """Slide-in toast notification from top-right corner.

    Displays service name, icon and unread count.
    Auto-dismisses after ``timeout_ms`` milliseconds.
    Clicking it emits ``clicked(service_id)``.
    """

    clicked = Signal(str)  # service_id

    _STACK: 'list[_ToastNotification]' = []  # active toasts (class-level)

    def __init__(self, service, parent=None, timeout_ms: int = 4000):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(300, 64)
        self._svc = service
        self._timeout = timeout_ms

        # Layout
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        # Colored icon
        icon_w = QLabel()
        icon_w.setFixedSize(36, 36)
        icon_w.setAlignment(Qt.AlignCenter)
        icon_w.setStyleSheet(
            f'background: {service.color}; border-radius: 8px; '
            f'font-size:14px; font-weight:bold; color:#fff;'
        )
        icon_w.setText(service.icon or service.name[:2].upper())
        lay.addWidget(icon_w)

        # Text
        txt = QVBoxLayout()
        txt.setSpacing(2)
        name_lbl = QLabel(service.name)
        name_lbl.setStyleSheet('font-weight:600; font-size:12px; color:#cdd6f4; background:transparent;')
        unread = getattr(service, 'unread', 0)
        msg_lbl = QLabel(f'{unread} mensagem(ns) não lida(s)')
        msg_lbl.setStyleSheet('font-size:11px; color:#a6adc8; background:transparent;')
        txt.addWidget(name_lbl)
        txt.addWidget(msg_lbl)
        lay.addLayout(txt, 1)

        self.setStyleSheet(
            'background: #1e1e2e; border-radius: 12px; '
            'border: 1px solid #313244;'
        )
        self.setCursor(Qt.PointingHandCursor)

        # Slide-in animation (moves from right+hidden → visible)
        self._anim = QPropertyAnimation(self, b'pos', self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # Auto-dismiss timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)
        self._timer.start(timeout_ms)

        _ToastNotification._STACK.append(self)

    def _get_target_pos(self) -> QPoint:
        parent = self.parent()
        stack_offset = len(_ToastNotification._STACK) - 1
        if parent:
            pr = parent.rect()
            local = QPoint(pr.width() - self.width() - 16,
                           48 + stack_offset * (self.height() + 8))
            # Qt.Tool windows are top-level: move() uses screen coords
            return parent.mapToGlobal(local)
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        return QPoint(screen.right() - self.width() - 16,
                      screen.top() + 48 + stack_offset * (self.height() + 8))

    def show_animated(self):
        target = self._get_target_pos()
        start = QPoint(target.x() + self.width() + 20, target.y())
        self.move(start)
        self.show()
        self._anim.setStartValue(start)
        self._anim.setEndValue(target)
        self._anim.start()

    def _dismiss(self):
        self._timer.stop()
        # Disconnect any previous finished connections to avoid double cleanup
        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        self._anim.setStartValue(self.pos())
        end = QPoint(self.pos().x() + self.width() + 20, self.pos().y())
        self._anim.setEndValue(end)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._cleanup)
        self._anim.start()

    def _cleanup(self):
        if self in _ToastNotification._STACK:
            _ToastNotification._STACK.remove(self)
        self.close()
        self.deleteLater()

    def mousePressEvent(self, event):
        self._timer.stop()
        self.clicked.emit(self._svc.id)
        self._dismiss()

    def paintEvent(self, event):  # noqa: N802
        """Explicit paint so the dark background renders on WA_TranslucentBackground."""
        from PySide6.QtGui import QPainter, QColor, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#313244'), 1))
        p.setBrush(QColor('#1e1e2e'))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
        p.end()


# ── Glass sidebar ─────────────────────────────────────────────────────────────

class _GlassSidebar(QWidget):  # pragma: no cover
    """Sidebar widget with a glassmorphism-style painted background."""

    def __init__(self, accent_color: str = '#7c6af7', parent=None):
        super().__init__(parent)
        self._accent = accent_color
        self.style: str = 'discord'
        self.opacity: int = 100          # 0-100%
        self.custom_bg: str = ''         # hex override
        self.custom_border: str = ''     # hex override
        self.setObjectName('sidebar')
        self.setStyleSheet('QWidget#sidebar { background: transparent; border-right: none; }')

    def set_accent(self, color: str):
        self._accent = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Apply global opacity
        if self.opacity < 100:
            p.setOpacity(self.opacity / 100.0)

        # Custom background override
        if self.custom_bg:
            p.fillRect(0, 0, w, h, QColor(self.custom_bg))
            border_c = QColor(self.custom_border) if self.custom_border else QColor(50, 50, 65, 160)
            p.setPen(border_c)
            p.drawLine(w - 1, 0, w - 1, h)
            super().paintEvent(event)
            return

        if self.style == 'arc':
            # Flat surface — clean, no gradient
            p.fillRect(0, 0, w, h, QColor('#1c1c23'))
            p.setPen(QColor(50, 50, 65, 120))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'notion':
            # Flat base — minimal, no effects
            p.fillRect(0, 0, w, h, QColor('#16161a'))
            p.setPen(QColor(46, 46, 61, 100))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'dock':
            # Glassmorphism — more transparent, stronger glow
            ac = QColor(self._accent)
            base = QColor(22, 22, 30, 240)
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, base)
            grad.setColorAt(1.0, QColor(
                min(255, 16 + int(ac.red() * 0.15)),
                min(255, 16 + int(ac.green() * 0.10)),
                min(255, 24 + int(ac.blue() * 0.22)), 245))
            p.fillRect(0, 0, w, h, grad)
            glow = QColor(self._accent)
            glow.setAlpha(40)
            glow2 = QColor(self._accent)
            glow2.setAlpha(0)
            bg = QLinearGradient(0, h - 150, 0, h)
            bg.setColorAt(0.0, glow2)
            bg.setColorAt(1.0, glow)
            p.fillRect(0, h - 150, w, 150, bg)
            p.setPen(QColor(50, 50, 65, 160))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'slack':
            # Slack: deep aubergine gradient
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor('#1a0525'))
            grad.setColorAt(1.0, QColor('#350d36'))
            p.fillRect(0, 0, w, h, grad)
            p.setPen(QColor(80, 40, 80, 120))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'spotify':
            # Spotify: near-black with subtle green accent
            p.fillRect(0, 0, w, h, QColor('#0a0a0a'))
            glow = QLinearGradient(0, h - 100, 0, h)
            glow.setColorAt(0.0, QColor(29, 185, 84, 0))
            glow.setColorAt(1.0, QColor(29, 185, 84, 15))
            p.fillRect(0, h - 100, w, 100, glow)
            p.setPen(QColor(40, 40, 40, 180))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'teams':
            # Teams: corporate dark blue
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor('#1b1b2f'))
            grad.setColorAt(1.0, QColor('#11111f'))
            p.fillRect(0, 0, w, h, grad)
            p.setPen(QColor(98, 100, 167, 60))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'telegram':
            # Telegram: dark with blue tint
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor('#0e1621'))
            grad.setColorAt(1.0, QColor('#17212b'))
            p.fillRect(0, 0, w, h, grad)
            p.setPen(QColor(42, 141, 197, 40))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'figma':
            # Figma: pure dark, ultra-clean
            p.fillRect(0, 0, w, h, QColor('#1e1e1e'))
            p.setPen(QColor(60, 60, 60, 100))
            p.drawLine(w - 1, 0, w - 1, h)
        elif self.style == 'linear':
            # Linear: very dark with subtle purple tint
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, QColor('#111115'))
            grad.setColorAt(1.0, QColor('#16141f'))
            p.fillRect(0, 0, w, h, grad)
            p.setPen(QColor(94, 106, 210, 30))
            p.drawLine(w - 1, 0, w - 1, h)
        else:
            # Discord — gradient + accent glow (default)
            ac = QColor(self._accent)
            base_top = QColor(26, 26, 36, 252)
            base_bot = QColor(
                min(255, 18 + int(ac.red() * 0.12)),
                min(255, 18 + int(ac.green() * 0.08)),
                min(255, 26 + int(ac.blue() * 0.18)), 255)
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0.0, base_top)
            grad.setColorAt(1.0, base_bot)
            p.fillRect(0, 0, w, h, grad)
            # Bottom glow
            glow_ac = QColor(self._accent)
            glow_ac.setAlpha(30)
            glow_ac2 = QColor(self._accent)
            glow_ac2.setAlpha(0)
            bot_grad = QLinearGradient(0, h - 120, 0, h)
            bot_grad.setColorAt(0.0, glow_ac2)
            bot_grad.setColorAt(1.0, glow_ac)
            p.fillRect(0, h - 120, w, 120, bot_grad)
            # Top accent strip
            ac_strip = QColor(self._accent)
            ac_strip.setAlpha(80)
            ac_strip2 = QColor(self._accent)
            ac_strip2.setAlpha(0)
            top_grad = QLinearGradient(0, 0, w, 0)
            top_grad.setColorAt(0, ac_strip)
            top_grad.setColorAt(1, ac_strip2)
            p.fillRect(0, 0, w, 2, top_grad)
            p.setPen(QColor(50, 50, 65, 200))
            p.drawLine(w - 1, 0, w - 1, h)

        super().paintEvent(event)


# ── Privacy overlay ────────────────────────────────────────────────────────────

class _PrivacyOverlay(QWidget):  # pragma: no cover
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
        _tick()  # keep splash alive
        self._init_encryption()
        self._workspaces: List[Workspace] = load_workspaces()
        self._active_workspace: Workspace = self._workspaces[0]
        self._services: list[Service] = self._active_workspace.services
        self._active_service: Optional[Service] = None
        self._active_account: Optional[Account] = None

        # (service_id, account_id) → ServiceView
        self._views: Dict[Tuple[str, str], ServiceView] = {}
        # service_id → QListWidgetItem
        self._svc_items: Dict[str, QListWidgetItem] = {}
        # group header widgets tracked for cleanup
        self._group_header_widgets: list = []

        # Lazy loading: track which service views have been initialized
        self._loaded_services: set = set()

        # Active tag filter (for tag chip clicking)
        self._active_tag_filter: Optional[str] = None

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

        # Load focus profile from settings
        settings = load_settings()
        _load_focus_profile(settings)
        _tick()

        self._setup_window()
        _tick()
        self._sidebar_compact: bool = load_settings().get('sidebar_compact', True)
        self._sidebar_style: str = load_settings().get('sidebar_style', 'discord')
        self._hover_anims: list = []  # kept for compat (unused since sidebar refactor)
        self._build_ui()
        _tick()
        self._setup_tray()
        self._setup_global_hotkey()
        self._setup_shortcuts()
        _tick()
        self._rich_tooltip = _RichTooltip()
        self._hibernate_timers: Dict[str, 'QTimer'] = {}
        self._hibernated: set = set()  # set of (service_id, account_id) keys
        self._setup_hibernate_timers()
        self._apply_theme(self._theme)

        # Re-apply sidebar width after show() so QSplitter honours the value
        # (setSizes() called before show() is often ignored by Qt's layout engine)
        _s0 = load_settings()
        _cw0 = _s0.get('sidebar_compact_width', 68)
        _ew0 = _s0.get('sidebar_expanded_width', 220)
        _iw0 = _cw0 if self._sidebar_compact else _s0.get('sidebar_width', _ew0)
        QTimer.singleShot(0, lambda: self._splitter.setSizes(
            [_iw0, max(1, self._splitter.width() - _iw0), 0]
        ))

        # Restore AI sidebar state from settings
        if load_settings().get('ai_sidebar_open', False):
            self._toggle_ai_sidebar()  # pragma: no cover

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
            self._select_service(self._services[0])  # pragma: no cover

        set_ad_block(load_settings().get('ad_block', True))
        self._check_updates(silent=True)

        # Pre-warm remaining services if preload_on_start is enabled
        if load_settings().get('preload_on_start', False) and len(self._services) > 1:
            self._schedule_service_preload(self._services[1:])

        # ── Lock screen ──────────────────────────────────────────────────────
        settings = load_settings()
        pin_hash = settings.get('pin_hash')
        if pin_hash:  # pragma: no cover
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
        from .workspace_schedule import load_schedule
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
            QTimer.singleShot(200, self._show_onboarding)  # pragma: no cover

        # ── Security monitor ─────────────────────────────────────────────────
        import sys as _sys
        if load_settings().get('security_monitor', True) and _sys.platform == 'win32':
            try:
                self._security_monitor = SecurityMonitor(self)
                self._security_monitor.threat_detected.connect(
                    lambda desc: ToastManager.show(self, f'⚠ {desc}', 'warning')
                )
                self._security_monitor.start()
            except Exception:
                self._security_monitor = None
        else:
            self._security_monitor = None

        # ── Service status checker ────────────────────────────────────────────
        if load_settings().get('show_service_status', False):
            try:
                svc_urls = [(s.id, s.accounts[0].url if s.accounts else 'https://example.com')
                            for s in self._services if s.accounts]
                self._status_checker = ServiceStatusChecker(svc_urls, self)
                self._status_checker.status_changed.connect(self._on_service_status_changed)
                self._status_checker.start()
            except Exception:
                self._status_checker = None
        else:
            self._status_checker = None

        # ── Audit log: record startup ────────────────────────────────────────
        _log_event('app_start')

        # ── Clipboard guard ──────────────────────────────────────────────────
        _cb_timeout = load_settings().get('clipboard_guard_timeout_ms', 30_000)
        if _cb_timeout > 0:
            try:
                from .clipboard_guard import ClipboardGuard
                self._clipboard_guard = ClipboardGuard(QApplication.instance(), _cb_timeout, self)
                self._clipboard_guard.cleared.connect(
                    lambda: ToastManager.show(self, _t('clipboard_cleared'), 'info')
                )
            except Exception:
                self._clipboard_guard = None
        else:
            self._clipboard_guard = None

    def resizeEvent(self, event):  # pragma: no cover
        super().resizeEvent(event)
        if hasattr(self, '_lock_screen') and self._lock_screen and self._lock_screen.isVisible():
            self._lock_screen.setGeometry(self.rect())
        self._update_privacy_overlay_size()

    def eventFilter(self, obj, event):  # pragma: no cover
        if event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress):
            self._last_activity = time.time()
        # Close search bar on Escape
        if event.type() == QEvent.KeyPress and hasattr(self, '_search_bar'):
            if obj is self._search_bar:
                if event.key() == Qt.Key_Escape:
                    self._hide_service_search()
                    return True
        # Hide rich tooltip when mouse leaves the service list viewport
        if event.type() == QEvent.Leave and hasattr(self, '_svc_list'):
            if obj is self._svc_list.viewport() and hasattr(self, '_rich_tooltip'):
                self._rich_tooltip.hide()
        # ── Rich tooltip on sidebar hover ─────────────────────────
        if hasattr(self, '_svc_list') and obj is self._svc_list.viewport():
            if event.type() == QEvent.MouseMove and not getattr(self, '_drag_active', False):
                pos = event.position().toPoint()
                item = self._svc_list.itemAt(pos)
                if item and self._sidebar_compact:
                    svc = item.data(_ROLE_SVC)
                    if svc:
                        rect = self._svc_list.visualItemRect(item)
                        global_rect = QRect(
                            self._svc_list.viewport().mapToGlobal(rect.topLeft()),
                            rect.size()
                        )
                        self._rich_tooltip.show_for(svc, global_rect)
                else:
                    self._rich_tooltip.hide()
        # ── Drag-to-reorder service list ──────────────────────────
        if hasattr(self, '_svc_list') and obj is self._svc_list.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                item = self._svc_list.itemAt(event.position().toPoint())
                if item:
                    self._drag_src_row = self._svc_list.row(item)
                    self._drag_active = False
            elif event.type() == QEvent.MouseMove and self._drag_src_row >= 0:
                if not self._drag_active:
                    self._drag_active = True
                    self._svc_list.setCursor(Qt.ClosedHandCursor)
                pos = event.position().toPoint()
                target = self._svc_list.itemAt(pos)
                if target:
                    target_row = self._svc_list.row(target)
                    # Show drop indicator line
                    rect = self._svc_list.visualItemRect(target)
                    mid = rect.center().y()
                    y = rect.top() if pos.y() < mid else rect.bottom()
                    self._drag_indicator.setGeometry(rect.x() + 4, y - 1, rect.width() - 8, 2)
                    self._drag_indicator.show()
                    self._drag_indicator.raise_()
                    if target_row != self._drag_src_row:
                        # Move in data model
                        svc = self._services.pop(self._drag_src_row)
                        self._services.insert(target_row, svc)
                        # Rebuild synchronously (drag needs immediate visual feedback)
                        self._do_rebuild_sidebar()
                        self._svc_list.setCurrentRow(target_row)
                        self._drag_src_row = target_row
                else:
                    self._drag_indicator.hide()
            elif event.type() == QEvent.MouseButtonRelease and self._drag_src_row >= 0:
                self._drag_indicator.hide()
                if self._drag_active:
                    self._save()
                    self._svc_list.setCursor(Qt.ArrowCursor)
                self._drag_src_row = -1
                self._drag_active = False
        return super().eventFilter(obj, event)

    # ── window setup ─────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):  # pragma: no cover
        from PySide6.QtGui import QShortcut
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

        # Theme toggle shortcut (Ctrl+Shift+T)
        theme_sc = QShortcut(QKeySequence('Ctrl+Shift+T'), self)
        theme_sc.activated.connect(self._toggle_theme)
        self._sc_objects['theme_toggle'] = theme_sc

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

        # Quick service search (Alt+S)
        search_sc = QShortcut(QKeySequence('Alt+S'), self)
        search_sc.activated.connect(self._show_service_search)
        self._sc_objects['svc_search'] = search_sc

        # Focus profile cycle (Ctrl+Shift+F)
        focus_sc = QShortcut(QKeySequence('Ctrl+Shift+F'), self)
        focus_sc.activated.connect(self._cycle_focus_profile)
        self._sc_objects['focus_profile'] = focus_sc

        # Notification center (Ctrl+Shift+N)
        notif_sc = QShortcut(QKeySequence('Ctrl+Shift+N'), self)
        notif_sc.activated.connect(self._toggle_notif_center)
        self._sc_objects['notif_center'] = notif_sc

        settings_sc = QShortcut(QKeySequence('Ctrl+,'), self)
        settings_sc.activated.connect(self._show_settings)
        self._sc_objects['settings'] = settings_sc

    def _kbd_select_service(self, idx: int):  # pragma: no cover
        if idx < len(self._services):
            self._select_service(self._services[idx])

    def _toggle_focus_mode(self):  # pragma: no cover
        self._sidebar.setVisible(not self._sidebar.isVisible())
        if self._active_service:
            self._refresh_header()

    def _zoom_in(self):  # pragma: no cover
        self._set_zoom(min(3.0, (self._active_service.zoom if self._active_service else 1.0) + 0.1))

    def _zoom_out(self):  # pragma: no cover
        self._set_zoom(max(0.3, (self._active_service.zoom if self._active_service else 1.0) - 0.1))

    def _zoom_reset(self):  # pragma: no cover
        self._set_zoom(1.0)

    def _set_zoom(self, factor: float):  # pragma: no cover
        if not self._active_service or not self._active_account:
            return
        self._active_service.zoom = round(factor, 2)
        key = (self._active_service.id, self._active_account.id)
        if key in self._views:
            self._views[key].set_zoom(factor)
        self._save()

    def _setup_window(self):  # pragma: no cover
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

    def _build_ui(self):  # pragma: no cover
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── SIDEBAR ────────────────────────────────────────────────────────────
        _sidebar_accent = ACCENTS.get(self._accent, ACCENTS['Iris'])
        _sb_settings = load_settings()
        self._sidebar = _GlassSidebar(_sidebar_accent)
        self._sidebar.style = self._sidebar_style
        self._sidebar.opacity = _sb_settings.get('sidebar_opacity', 100)
        self._sidebar.custom_bg = _sb_settings.get('sidebar_custom_bg', '')
        self._sidebar.custom_border = _sb_settings.get('sidebar_custom_border', '')
        self._glass_sidebar = self._sidebar
        self._sidebar.setMinimumWidth(64)

        sb_layout = QVBoxLayout(self._sidebar)
        sb_layout.setContentsMargins(0, 12, 0, 8)
        sb_layout.setSpacing(0)

        # Stylized 'Orbit' text logo with accent gradient
        _accent_hex = ACCENTS.get(self._accent, ACCENTS['Iris'])
        self._logo_label = QLabel('O')
        self._logo_label.setAlignment(Qt.AlignCenter)
        self._logo_label.setFixedHeight(40)
        self._logo_label.setStyleSheet(
            f'background: transparent; color: {_accent_hex};'
            f' font-size: 22px; font-weight: 800; font-family: Inter, Segoe UI, sans-serif;'
            f' letter-spacing: 2px;'
        )
        if not self._sidebar_compact:
            self._logo_label.setText('Orbit')
        sb_layout.addWidget(self._logo_label)
        sb_layout.addSpacing(8)

        # Workspace switcher — hidden when workspaces_enabled=False
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
        _ws_enabled = load_settings().get('workspaces_enabled', True)
        self._ws_btn.setVisible(_ws_enabled)
        sb_layout.addWidget(self._ws_btn)
        sb_layout.addSpacing(4)

        # Separator between workspace button and service list
        self._sep_top = QFrame()
        self._sep_top.setFixedHeight(1)
        self._sep_top.setStyleSheet('background-color: #2e2e3d; border: none; margin: 2px 8px;')
        self._sep_top.setVisible(_ws_enabled)
        sb_layout.addWidget(self._sep_top)
        sb_layout.addSpacing(4)

        # ── Quick service search bar (hidden by default, Alt+S to show) ──────
        self._search_bar = QLineEdit()
        self._search_bar.setObjectName('svcSearchBar')
        self._search_bar.setPlaceholderText(_t('search_services'))
        self._search_bar.setVisible(False)
        self._search_bar.setFixedHeight(28)
        self._search_bar.setStyleSheet(
            'QLineEdit { background:#2a2a3a; border:1px solid #3e3e52; '
            'border-radius:6px; padding:2px 8px; color:#cdd6f4; font-size:12px; }'
        )
        self._search_bar.textChanged.connect(self._filter_sidebar_by_search)
        self._search_bar.installEventFilter(self)
        sb_layout.addWidget(self._search_bar)

        # ── Service list (QListWidget + ServiceDelegate) ──────────────────────
        self._svc_list = QListWidget()
        self._svc_list.setObjectName('svcList')
        self._svc_list.setFrameShape(QFrame.NoFrame)
        self._svc_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._svc_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._svc_list.setSpacing(1)
        self._svc_list.setSelectionMode(QListWidget.SingleSelection)
        self._svc_list.setMouseTracking(True)
        self._svc_list.viewport().setMouseTracking(True)

        # Delegate must be created AFTER svc_list and passed as parent so that
        # self.parent() in _tick_hover correctly returns the QListWidget.
        self._svc_delegate = ServiceDelegate(self._svc_list)
        self._svc_delegate.compact = self._sidebar_compact
        self._svc_delegate.style = self._sidebar_style
        self._svc_list.setItemDelegate(self._svc_delegate)
        self._svc_list.setStyleSheet(
            'QListWidget { background: transparent; border: none; outline: none; }'
            'QListWidget::item { border: none; background: transparent; }'
            'QListWidget::item:selected { background: transparent; }'
        )
        # Drag-to-reorder (custom implementation with visual indicator)
        self._svc_list.setDragDropMode(QListWidget.NoDragDrop)
        self._drag_src_row = -1
        self._drag_active = False
        self._drag_indicator = QFrame(self._svc_list.viewport())
        self._drag_indicator.setFixedHeight(2)
        self._drag_indicator.setStyleSheet('background-color: #7c6af7; border-radius: 1px;')
        self._drag_indicator.hide()
        self._svc_list.viewport().installEventFilter(self)

        # Signals
        self._svc_list.itemClicked.connect(self._on_svc_item_clicked)
        self._svc_list.currentItemChanged.connect(
            lambda cur, prev: self._svc_delegate.animate_selection() if cur else None
        )
        self._svc_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._svc_list.customContextMenuRequested.connect(self._on_svc_ctx_menu)
        self._svc_list.itemEntered.connect(self._on_svc_item_entered)
        self._svc_list.viewport().installEventFilter(self)

        sb_layout.addWidget(self._svc_list, 1)

        # Separator between service list and bottom bar
        _sep_bot = QFrame()
        _sep_bot.setFixedHeight(1)
        _sep_bot.setStyleSheet('background-color: #2e2e3d; border: none; margin: 2px 8px;')
        sb_layout.addWidget(_sep_bot)

        # ── Bottom action bar: [⚙ Settings] [+ Add] [‹ Collapse] ─────────────
        self._bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(self._bottom_bar)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        bottom_layout.setSpacing(0)

        def _mk_bar_btn(icon_name: str, tooltip: str, slot) -> QPushButton:
            btn = QPushButton()
            btn.setIcon(svg_icon(icon_name, 18, '#6c7086'))
            btn.setIconSize(QSize(18, 18))
            btn.setObjectName('addBtn')
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            return btn

        settings_btn = _mk_bar_btn('cog-6-tooth', 'Configurações  (Ctrl+,)', self._show_settings)
        add_btn = _mk_bar_btn('plus-circle', 'Adicionar serviço', self._add_service)
        self._theme_btn = _mk_bar_btn(
            'moon' if self._theme == 'dark' else 'sun',
            'Alternar tema (Ctrl+Shift+T)',
            self._toggle_theme,
        )
        self._compact_btn = _mk_bar_btn(
            'chevron-double-right' if self._sidebar_compact else 'chevron-double-left',
            'Recolher sidebar',
            self._toggle_compact,
        )
        bottom_layout.addWidget(settings_btn)
        bottom_layout.addWidget(add_btn)
        bottom_layout.addWidget(self._theme_btn)
        bottom_layout.addWidget(self._compact_btn)
        sb_layout.addWidget(self._bottom_bar)

        # ── CONTENT AREA ───────────────────────────────────────────────────────
        content = QWidget()
        self._content_widget = content
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
        self._ai_panel = self._build_ai_sidebar()
        _s = load_settings()
        self._sidebar_position = _s.get('sidebar_position', 'left')
        if self._sidebar_position == 'right':
            self._splitter.addWidget(content)
            self._splitter.addWidget(self._ai_panel)
            self._splitter.addWidget(self._sidebar)
        else:
            self._splitter.addWidget(self._sidebar)
            self._splitter.addWidget(content)
            self._splitter.addWidget(self._ai_panel)
        self._splitter.setCollapsible(0, False)
        self._splitter.setCollapsible(1, False)
        self._splitter.setCollapsible(2, True)
        _compact_w  = _s.get('sidebar_compact_width', 68)
        _expanded_w = _s.get('sidebar_expanded_width', 220)
        _init_w = _compact_w if self._sidebar_compact else _s.get('sidebar_width', _expanded_w)
        if self._sidebar_position == 'right':
            self._splitter.setSizes([1220, 0, _init_w])
        else:
            self._splitter.setSizes([_init_w, 1220, 0])
        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        root.addWidget(self._splitter, 1)

        # Notification center panel (overlay on right side of central)
        self._notif_center = NotificationCenter(central, self._get_accent_color())

        self._rebuild_sidebar()
        self._update_workspace_btn()

    def _build_ai_sidebar(self) -> QWidget:  # pragma: no cover
        """Placeholder AI sidebar panel (collapsed by default)."""
        panel = QWidget()
        panel.setObjectName('aiPanel')
        panel.setMinimumWidth(0)
        panel.setMaximumWidth(0)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        return panel

    def _toggle_ai_sidebar(self):  # pragma: no cover
        """Toggle the AI sidebar panel open/closed."""
        if not hasattr(self, '_ai_panel'):
            return
        sizes = self._splitter.sizes()
        if len(sizes) >= 3:
            new_ai = 0 if sizes[2] > 0 else 320
            self._splitter.setSizes([sizes[0], sizes[1] - new_ai, new_ai])

    def _make_welcome(self) -> QWidget:  # pragma: no cover
        w = QWidget()
        w.setObjectName('welcome')
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        _lottie_path = LottieLabel.lottie_path()
        if os.path.exists(_lottie_path):
            logo = LottieLabel(_lottie_path, size=96, fps=30, skip_frames=2)
        else:
            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            _welcome_px = _orbit_logo_pixmap(96)
            logo.setPixmap(_welcome_px)
            logo.setStyleSheet('background: transparent;')
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

    def _build_ai_sidebar(self) -> QWidget:  # pragma: no cover
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

    def _on_ai_provider_changed(self, index: int):  # pragma: no cover
        if not hasattr(self, '_ai_view') or self._ai_view is None:
            return
        provider = self._ai_provider_combo.currentText()
        url = self._AI_URLS.get(provider, 'https://chat.openai.com')
        self._ai_view.load(QUrl(url))

    def _toggle_ai_sidebar(self):  # pragma: no cover
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

    def _toggle_privacy_mode(self):  # pragma: no cover
        self._privacy_mode = not self._privacy_mode
        if self._privacy_mode:
            self._privacy_overlay.show()
            self._privacy_overlay.raise_()
            self._privacy_overlay.resize(self._stack.size())
        else:
            self._privacy_overlay.hide()
        if hasattr(self, '_tray_privacy_act'):
            self._tray_privacy_act.setChecked(self._privacy_mode)

    def _update_privacy_overlay_size(self):  # pragma: no cover
        if hasattr(self, '_privacy_overlay'):
            self._privacy_overlay.resize(self._stack.size())

    # ── quick search ──────────────────────────────────────────────────────────

    def _show_service_search(self):  # pragma: no cover
        """Show the sidebar search bar and focus it (Alt+S)."""
        if not hasattr(self, '_search_bar'):
            return
        self._search_bar.setVisible(True)
        self._search_bar.setFocus()
        self._search_bar.selectAll()

    def _hide_service_search(self):  # pragma: no cover
        """Hide and clear the sidebar search bar."""
        if not hasattr(self, '_search_bar'):
            return
        self._search_bar.clear()
        self._search_bar.setVisible(False)
        self._filter_sidebar_by_search('')

    def _filter_sidebar_by_search(self, text: str):  # pragma: no cover
        """Show/hide service items based on search text."""
        query = text.strip().lower()
        for svc_id, item in self._svc_items.items():
            svc = item.data(_ROLE_SVC)
            name = svc.name.lower() if svc else ''
            item.setHidden(bool(query) and query not in name)

    # ── tag filter ────────────────────────────────────────────────────────────

    def _toggle_tag_filter(self, tag: str):  # pragma: no cover
        """Toggle filtering sidebar by a tag chip."""
        if self._active_tag_filter == tag:
            self._active_tag_filter = None
        else:
            self._active_tag_filter = tag
        self._rebuild_sidebar()

    # ── service enable/disable ────────────────────────────────────────────────

    def _toggle_service_enabled(self, service: Service):  # pragma: no cover
        """Enable or disable a service."""
        service.enabled = not service.enabled
        if not service.enabled:
            # Unload views for this service
            for acc in service.accounts:
                key = (service.id, acc.id)
                if key in self._views:
                    view = self._views.pop(key)
                    self._stack.removeWidget(view)
                    view.deleteLater()
            self._loaded_services.discard(service.id)
            if self._active_service and self._active_service.id == service.id:
                self._active_service = None
                self._active_account = None
                self._stack.setCurrentWidget(self._dashboard if self._services else self._welcome)
                self._refresh_header()
        else:
            # Re-select to load it
            self._select_service(service)
        self._rebuild_sidebar()
        self._save()

    # ── focus profiles ────────────────────────────────────────────────────────

    def _show_focus_profile_menu(self):  # pragma: no cover
        """Show focus profile picker menu below the header button."""
        menu = QMenu(self)
        active = _get_focus_profile()
        for p_key in _PROFILE_ORDER:
            p_label = _PROFILE_LABELS.get(p_key, p_key)
            act = menu.addAction(p_label)
            act.setCheckable(True)
            act.setChecked(p_key == active)
            act.triggered.connect(lambda _, pk=p_key: self._set_focus_profile(pk))
        if hasattr(self, '_focus_profile_btn'):
            pos = self._focus_profile_btn.mapToGlobal(
                self._focus_profile_btn.rect().bottomLeft()
            )
            menu.exec(pos)

    def _cycle_focus_profile(self):  # pragma: no cover
        """Cycle through focus profiles (Ctrl+Shift+F)."""
        profile = _cycle_focus_profile()
        settings = load_settings()
        _save_focus_profile(settings)
        save_settings(settings)
        label = _PROFILE_LABELS.get(profile, profile)
        ToastManager.show(self, f'Perfil: {label}', 'info')
        self._update_focus_profile_ui()

    def _set_focus_profile(self, profile: str):  # pragma: no cover
        """Set a specific focus profile."""
        _set_focus_profile(profile)
        settings = load_settings()
        _save_focus_profile(settings)
        save_settings(settings)
        self._update_focus_profile_ui()

    def _update_focus_profile_ui(self):  # pragma: no cover
        """Update the focus profile button and tray menu to reflect the active profile."""
        profile = _get_focus_profile()
        label = _PROFILE_LABELS.get(profile, profile)
        if hasattr(self, '_focus_profile_btn'):
            self._focus_profile_btn.setText(label)
        if hasattr(self, '_tray_profile_actions'):
            for p, act in self._tray_profile_actions.items():
                act.setChecked(p == profile)
        # Apply DND from profile
        if _dnd_in_profile():
            if self._dnd_until is None:
                self._set_dnd(60 * 24)  # 24h DND for 'off' profile
        else:
            if self._dnd_until is not None:
                self._set_dnd(None)

    # ── audit log viewer ──────────────────────────────────────────────────────

    def _show_audit_log(self):  # pragma: no cover
        """Show the audit log in a dialog."""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget,
                                        QTableWidgetItem, QDialogButtonBox, QLabel)
        from .audit_log import get_events
        dlg = QDialog(self)
        dlg.setWindowTitle(_t('audit_log'))
        dlg.setMinimumSize(600, 400)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel(f'📋 {_t("audit_log")}')
        title.setStyleSheet('font-size:14px; font-weight:bold;')
        layout.addWidget(title)

        events = get_events()
        table = QTableWidget(len(events), 3)
        table.setHorizontalHeaderLabels(['Timestamp', 'Event', 'Detail'])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        for i, ev in enumerate(reversed(events)):
            table.setItem(i, 0, QTableWidgetItem(ev.get('ts', '')))
            table.setItem(i, 1, QTableWidgetItem(ev.get('event', '')))
            table.setItem(i, 2, QTableWidgetItem(ev.get('detail', '')))

        table.resizeColumnsToContents()
        layout.addWidget(table, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def _rebuild_sidebar(self):  # pragma: no cover
        """Debounced sidebar rebuild — coalesces rapid calls into one."""
        if not hasattr(self, '_rebuild_timer'):
            self._rebuild_timer = QTimer(self)
            self._rebuild_timer.setSingleShot(True)
            self._rebuild_timer.setInterval(50)
            self._rebuild_timer.timeout.connect(self._do_rebuild_sidebar)
        self._rebuild_timer.start()

    def _do_rebuild_sidebar(self):  # pragma: no cover
        # Clear all items
        self._svc_list.clear()
        self._svc_items.clear()
        self._group_header_widgets = []

        from .catalog import get_entry

        # Clear legacy groups — groups are no longer used
        if self._active_workspace and getattr(self._active_workspace, 'groups', None):
            self._active_workspace.groups = []

        def _add_svc_item(svc: Service, indent: int = 0):
            if self._active_tag_filter and self._active_tag_filter not in getattr(svc, 'tags', []):
                return

            item = QListWidgetItem()
            item.setData(_ROLE_SVC, svc)
            item.setData(_ROLE_BADGE, getattr(svc, 'unread', 0))
            item.setData(_ROLE_STATUS, '')
            item.setData(_ROLE_PIXMAP, None)

            # Load cached icon (white fill for visibility on colored box)
            from .brand_icons import brand_icon, has_brand_icon
            entry = get_entry(svc.service_type)
            if has_brand_icon(svc.service_type):
                px = brand_icon(svc.service_type, 26, '#FFFFFF')
                if not px.isNull():
                    item.setData(_ROLE_PIXMAP, px)
            elif entry and entry.favicon_url:
                from .cache import get_cached_pixmap
                cached = get_cached_pixmap(entry.favicon_url)
                if cached:
                    item.setData(_ROLE_PIXMAP, cached)

            item.setToolTip('')  # Badge already shows count — no tooltip needed
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

            self._svc_list.addItem(item)
            self._svc_items[svc.id] = item

        # Render all services (groups removed — use workspaces instead)
        for svc in self._services:
            _add_svc_item(svc, indent=0)

        if hasattr(self, '_icon_fetcher'):
            self._fetch_service_icons()

        if hasattr(self, '_dashboard'):
            self._dashboard.refresh(self._services)
            if not self._active_service:
                if self._services:
                    self._stack.setCurrentWidget(self._dashboard)
                else:
                    self._stack.setCurrentWidget(self._welcome)

    def _make_group_header(self, group: ServiceGroup) -> QWidget:  # pragma: no cover
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

    def _toggle_group(self, group: ServiceGroup):  # pragma: no cover
        group.collapsed = not group.collapsed
        self._save()
        self._rebuild_sidebar()

    def _show_group_ctx_menu(self, group: ServiceGroup, global_pos):  # pragma: no cover
        menu = QMenu(self)
        rename_act = menu.addAction('✏️ Renomear grupo')
        remove_act = menu.addAction('🗑️ Remover grupo')
        action = menu.exec(global_pos)
        if action == rename_act:
            self._rename_group(group)
        elif action == remove_act:
            self._remove_group(group)

    def _rename_group(self, group: ServiceGroup):  # pragma: no cover
        name, ok = QInputDialog.getText(self, 'Renomear grupo', 'Novo nome:', text=group.name)
        if ok and name.strip():
            group.name = name.strip()
            self._save()
            self._rebuild_sidebar()

    def _remove_group(self, group: ServiceGroup):  # pragma: no cover
        self._active_workspace.groups.remove(group)
        self._save()
        self._rebuild_sidebar()

    def _create_group_for(self, svc: Service):  # pragma: no cover
        import uuid
        name, ok = QInputDialog.getText(self, 'Criar grupo', 'Nome do grupo:')
        if ok and name.strip():
            group = ServiceGroup(id=str(uuid.uuid4()), name=name.strip(), service_ids=[svc.id])
            self._active_workspace.groups.append(group)
            self._save()
            self._rebuild_sidebar()

    def _move_to_group(self, svc: Service, group_id):  # pragma: no cover
        for g in self._active_workspace.groups:
            if svc.id in g.service_ids:
                g.service_ids.remove(svc.id)
        if group_id:
            target = next((g for g in self._active_workspace.groups if g.id == group_id), None)
            if target and svc.id not in target.service_ids:
                target.service_ids.append(svc.id)
        self._save()
        self._rebuild_sidebar()

    def _toggle_compact(self):  # pragma: no cover
        self._sidebar_compact = not self._sidebar_compact
        settings = load_settings()
        settings['sidebar_compact'] = self._sidebar_compact
        save_settings(settings)

        compact_w  = settings.get('sidebar_compact_width', 68)
        expanded_w = settings.get('sidebar_expanded_width', 220)
        target_w = compact_w if self._sidebar_compact else expanded_w
        start_w = self._splitter.sizes()[0]

        # Use QPropertyAnimation on sidebar min/max width for smooth animation
        if hasattr(self, '_compact_anim_min'):
            self._compact_anim_min.stop()
            self._compact_anim_max.stop()

        self._compact_anim_min = QPropertyAnimation(self._sidebar, b'minimumWidth', self)
        self._compact_anim_max = QPropertyAnimation(self._sidebar, b'maximumWidth', self)

        for anim, start, end in [
            (self._compact_anim_min, start_w, target_w),
            (self._compact_anim_max, start_w, target_w),
        ]:
            anim.setDuration(200)
            anim.setEasingCurve(QEasingCurve.InOutCubic)
            anim.setStartValue(start)
            anim.setEndValue(end)

        def _on_compact_anim_done():
            self._sidebar.setMinimumWidth(64)
            self._sidebar.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
            total = sum(self._splitter.sizes())
            self._splitter.setSizes([target_w, total - target_w])
            # Notify delegate and refresh list layout
            self._svc_delegate.compact = self._sidebar_compact
            if hasattr(self, '_logo_label'):
                self._logo_label.setText('O' if self._sidebar_compact else 'Orbit')
            self._svc_list.scheduleDelayedItemsLayout()
            self._svc_list.viewport().update()
            self._rebuild_sidebar()
            self._update_compact_btn()

        self._compact_anim_max.finished.connect(_on_compact_anim_done)
        self._compact_anim_min.start()
        self._compact_anim_max.start()

    def _animate_compact_step(self):  # pragma: no cover
        """Legacy stub — kept for compatibility but no longer used."""
        pass

    def _update_compact_btn(self):  # pragma: no cover
        if hasattr(self, '_compact_btn'):
            icon_name = 'chevron-double-right' if self._sidebar_compact else 'chevron-double-left'
            self._compact_btn.setIcon(svg_icon(icon_name, 14, '#6e6e8a'))
            self._compact_btn.setIconSize(QSize(14, 14))

    def _on_splitter_moved(self, pos: int, index: int):  # pragma: no cover
        sizes = self._splitter.sizes()
        settings = load_settings()
        settings['sidebar_width'] = sizes[0]
        save_settings(settings)

    def _fetch_service_icons(self):  # pragma: no cover
        from .catalog import get_entry
        seen_urls: set = set()
        for svc in self._services:
            entry = get_entry(svc.service_type)
            if entry and entry.favicon_url and entry.favicon_url not in seen_urls:
                seen_urls.add(entry.favicon_url)
                self._icon_fetcher.fetch(entry.favicon_url)

    def _on_icon_fetched(self, url: str, pixmap: QPixmap):  # pragma: no cover
        from .catalog import get_entry
        for svc in self._services:
            entry = get_entry(svc.service_type)
            if entry and entry.favicon_url == url:
                item = self._svc_items.get(svc.id)
                if item:
                    item.setData(_ROLE_PIXMAP, pixmap)
                    self._svc_list.viewport().update()

    # ── workspace ────────────────────────────────────────────────────────────

    def set_workspaces_enabled(self, enabled: bool) -> None:  # pragma: no cover
        """Show or hide the workspace switcher in the sidebar."""
        s = load_settings()
        s['workspaces_enabled'] = enabled
        save_settings(s)
        if hasattr(self, '_ws_btn'):
            self._ws_btn.setVisible(enabled)
        if hasattr(self, '_sep_top'):
            self._sep_top.setVisible(enabled)

    def _toggle_theme(self):  # pragma: no cover
        new_theme = 'light' if self._theme == 'dark' else 'dark'
        self._apply_theme(new_theme)
        icon_name = 'moon' if new_theme == 'dark' else 'sun'
        self._theme_btn.setIcon(svg_icon(icon_name, 18, '#6c7086'))

    def _apply_theme(self, theme: str):  # pragma: no cover
        self._theme = theme
        accent_color = ACCENTS.get(self._accent, ACCENTS['Iris'])
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

    def _set_accent(self, name: str):  # pragma: no cover
        self._accent = name
        s = load_settings()
        s['accent'] = name
        save_settings(s)
        self._apply_theme(self._theme)
        ToastManager.show(self, f'Tema {name} aplicado!', 'success')

    def _update_workspace_btn(self):  # pragma: no cover
        name = self._active_workspace.name
        fm = self._ws_btn.fontMetrics()
        available = self._ws_btn.width() - 20  # account for padding
        if available < 30:
            available = 100  # fallback before first paint
        elided = fm.elidedText(name, Qt.ElideRight, available)
        self._ws_btn.setText(f'{elided} ▾')

    def _show_workspace_menu(self):  # pragma: no cover
        menu = QMenu(self)
        for ws in self._workspaces:
            act = menu.addAction(ws.name)
            act.setCheckable(True)
            act.setChecked(ws.id == self._active_workspace.id)
            act.triggered.connect(lambda _, w=ws: self._switch_workspace(w))
        menu.addSeparator()
        menu.addAction('＋ Novo workspace').triggered.connect(self._add_workspace)
        menu.addSeparator()
        rename_act = menu.addAction('✏  Renomear workspace atual')
        rename_act.triggered.connect(self._rename_workspace)
        delete_act = menu.addAction('🗑  Excluir workspace atual')
        delete_act.setEnabled(len(self._workspaces) > 1)
        delete_act.triggered.connect(self._delete_workspace)
        menu.exec(self._ws_btn.mapToGlobal(self._ws_btn.rect().bottomLeft()))

    def _show_workspace_ctx_menu(self, global_pos):  # pragma: no cover
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
        # Apply global accent (workspace no longer overrides)
        global_accent = ACCENTS.get(self._accent, ACCENTS['Iris'])
        tokens = get_tokens(self._theme, global_accent)
        self.setStyleSheet(tokens.qss())
        if hasattr(self, '_glass_sidebar'):
            self._glass_sidebar.set_accent(global_accent)
            self._glass_sidebar.setStyleSheet(
                'QWidget#sidebar { background: transparent; border-right: none; }'
            )
        _log_event('workspace_switched', ws.name)

    def _add_workspace(self):  # pragma: no cover
        from .models import new_id
        dlg = EditWorkspaceDialog(parent=self)
        dlg.setWindowTitle('Novo workspace')
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.get_name()
        if name:
            ws = Workspace(id=new_id('ws'), name=name)
            self._workspaces.append(ws)
            self._switch_workspace(ws)
            self._save()

    def _rename_workspace(self):  # pragma: no cover
        dlg = EditWorkspaceDialog(
            name=self._active_workspace.name,
            parent=self,
        )
        dlg.setWindowTitle('Editar workspace')
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.get_name()
        if name:
            self._active_workspace.name = name
            self._update_workspace_btn()
            self._save()

    def _delete_workspace(self):  # pragma: no cover
        if len(self._workspaces) <= 1:
            return
        dlg = ConfirmDialog(f'Excluir workspace "{self._active_workspace.name}" e todos os seus serviços?', self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._workspaces.remove(self._active_workspace)
        self._switch_workspace(self._workspaces[0])
        self._save()

    # ── header ────────────────────────────────────────────────────────────────

    def _refresh_header(self):  # pragma: no cover
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

        # Focus profile button
        active_profile = _get_focus_profile()
        profile_label = _PROFILE_LABELS.get(active_profile, active_profile)
        self._focus_profile_btn = QPushButton(profile_label)
        self._focus_profile_btn.setObjectName('hBtn')
        self._focus_profile_btn.setFixedHeight(24)
        self._focus_profile_btn.setMinimumWidth(70)
        self._focus_profile_btn.setCursor(Qt.PointingHandCursor)
        self._focus_profile_btn.setToolTip(f'{_t("focus_profile")} (Ctrl+Shift+F para ciclar)')
        self._focus_profile_btn.setStyleSheet(
            'QPushButton { font-size:10px; padding:0 6px; }'
        )
        self._focus_profile_btn.clicked.connect(self._show_focus_profile_menu)
        self._header_layout.addWidget(self._focus_profile_btn)

        # Privacy mode button
        privacy_icon_name = 'eye-slash' if self._privacy_mode else 'eye'
        privacy_btn = QPushButton()
        privacy_btn.setIcon(svg_icon(privacy_icon_name, 18, '#6c7086'))
        privacy_btn.setIconSize(QSize(18, 18))
        privacy_btn.setObjectName('hBtn')
        privacy_btn.setFixedSize(32, 32)
        privacy_btn.setToolTip('Modo Privacidade (Ctrl+Shift+P)')
        privacy_btn.setCursor(Qt.PointingHandCursor)
        privacy_btn.setCheckable(True)
        privacy_btn.setChecked(self._privacy_mode)
        privacy_btn.clicked.connect(self._toggle_privacy_mode)
        self._header_layout.addWidget(privacy_btn)

        # AI sidebar toggle button
        ai_btn = QPushButton()
        ai_btn.setIcon(svg_icon('sparkles', 18, '#6c7086'))
        ai_btn.setIconSize(QSize(18, 18))
        ai_btn.setObjectName('hBtn')
        ai_btn.setFixedSize(32, 32)
        ai_btn.setToolTip('Painel IA (Ctrl+Shift+A)')
        ai_btn.setCursor(Qt.PointingHandCursor)
        ai_btn.clicked.connect(self._toggle_ai_sidebar)
        self._header_layout.addWidget(ai_btn)

        # Notification history button
        hist_btn = QPushButton()
        hist_btn.setIcon(svg_icon('bell', 18, '#6c7086'))
        hist_btn.setIconSize(QSize(18, 18))
        hist_btn.setObjectName('hBtn')
        hist_btn.setFixedSize(32, 32)
        hist_btn.setToolTip('Histórico de notificações')
        hist_btn.setCursor(Qt.PointingHandCursor)
        hist_btn.clicked.connect(self._show_notif_history_panel)
        self._header_layout.addWidget(hist_btn)

        # DND button
        dnd_icon = 'bell-slash' if self._is_dnd_active() else 'bell'
        dnd_btn = QPushButton()
        dnd_btn.setIcon(svg_icon(dnd_icon, 18, '#6c7086'))
        dnd_btn.setIconSize(QSize(18, 18))
        dnd_btn.setObjectName('hBtn')
        dnd_btn.setFixedSize(32, 32)
        dnd_btn.setToolTip('Não perturbe (Ctrl+D)')
        dnd_btn.setCursor(Qt.PointingHandCursor)
        dnd_btn.clicked.connect(self._show_dnd_menu)
        self._header_layout.addWidget(dnd_btn)

        # Focus toggle button
        focus_icon = 'chevron-left' if self._sidebar.isVisible() else 'chevron-right'
        focus_btn = QPushButton()
        focus_btn.setIcon(svg_icon(focus_icon, 18, '#6c7086'))
        focus_btn.setIconSize(QSize(18, 18))
        focus_btn.setObjectName('hBtn')
        focus_btn.setFixedSize(32, 32)
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
            b.setIcon(svg_icon(icon_name, 18, ic_color))
            b.setIconSize(QSize(18, 18))
            b.setObjectName(name_id)
            b.setFixedSize(32, 32)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            self._header_layout.addWidget(b)

    # ── selection ─────────────────────────────────────────────────────────────

    def _select_service(self, service: Service):  # pragma: no cover
        # Skip disabled services
        if not getattr(service, 'enabled', True):
            return
        # Record time on previous service
        if self._active_service and self._service_start_time:
            elapsed = time.time() - self._service_start_time
            record_session(self._active_service.id, self._active_service.name, elapsed)
        self._service_start_time = time.time()
        self._active_service = service
        self._reset_hibernate_timer(service)
        # Update visual selection in the service list
        active_item = self._svc_items.get(service.id)
        if active_item:
            self._svc_list.setCurrentItem(active_item)
        else:
            self._svc_list.clearSelection()
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

    def _select_service_by_id(self, service_id: str):  # pragma: no cover
        """Select a service by its ID — used by toast click handler."""
        svc = next((s for s in self._services if s.id == service_id), None)
        if svc:
            self.show()
            self.raise_()
            self.activateWindow()
            self._select_service(svc)

    def _select_account(self, account: Account):  # pragma: no cover
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
            # Lazy loading: mark this service as loaded
            self._loaded_services.add(self._active_service.id)
            view = ServiceView(account.profile_name, account.url,
                               service_type=self._active_service.service_type,
                               custom_css=self._active_service.custom_css,
                               custom_js=self._active_service.custom_js,
                               zoom=self._active_service.zoom,
                               incognito=getattr(self._active_service, 'incognito', False),
                               spellcheck=getattr(self._active_service, 'spellcheck', True))
            view.badge_changed.connect(
                lambda count, svc=self._active_service: self._update_badge(svc, count)
            )
            view.notification_received.connect(
                lambda title, body, svc=self._active_service: self._on_push_notification(svc, title, body)
            )
            view.load_status_changed.connect(
                lambda s, sid=self._active_service.id: self._on_load_status(sid, s)
            )
            # Wrap view in a stacked widget with skeleton overlay
            from .skeleton import SkeletonWidget
            wrapper = QStackedWidget()
            wrapper.setObjectName('viewWrapper')
            skeleton = SkeletonWidget()
            wrapper.addWidget(skeleton)  # index 0 = skeleton
            wrapper.addWidget(view)      # index 1 = webview
            wrapper.setCurrentIndex(0)   # show skeleton initially
            view._wrapper = wrapper
            view._skeleton = skeleton
            view.load_status_changed.connect(
                lambda s, w=wrapper: w.setCurrentIndex(1) if s == 'ready' else None
            )
            self._views[key] = view
            self._stack.addWidget(wrapper)
            self._status_badge.set_status('connecting')

        self._wake_service(self._active_service, account)
        # Mark only the new view as active (controls badge-clear permission)
        for v in self._views.values():
            v.active = False
        self._views[key].active = True
        target = getattr(self._views[key], '_wrapper', self._views[key])
        self._fade_switch(target)

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

    def _update_badge(self, service: Service, count: int):  # pragma: no cover
        prev = service.unread
        service.unread = count
        item = self._svc_items.get(service.id)
        if item:
            item.setData(_ROLE_BADGE, count)
            self._svc_list.viewport().update()
            # Badge pulse animation when count increases
            if count > prev and count > 0:
                self._pulse_badge(item)
        self._update_title_badge()
        if count > prev and count > 0:
            add_notification(service.id, service.name, f'{service.name}: {count} mensagem(s)')
            is_active = self._active_service and self._active_service.id == service.id
            svc_tags = getattr(service, 'tags', [])
            muted_by_profile = _svc_muted_by_profile(svc_tags)
            win_focused = self.isActiveWindow()
            should_notify = (not is_active or not win_focused)
            if should_notify and not self._is_dnd_active() and not muted_by_profile:
                notif_style = self._settings.get('notification_style', 'orbit')
                # Track last toast time per service for deduplication (badge vs push)
                if not hasattr(self, '_last_toast_time'):
                    self._last_toast_time: dict = {}
                import time as _time
                now = _time.monotonic()
                last = self._last_toast_time.get(service.id, 0)
                if now - last > 2.0:  # debounce 2s to avoid badge+push duplicates
                    if notif_style in ('orbit', 'both'):
                        self._show_toast(service)
                        self._last_toast_time[service.id] = now
                    if notif_style in ('system', 'both'):
                        if hasattr(self, '_tray') and self._tray.isVisible():
                            self._tray.showMessage(
                                service.name,
                                f'{count} mensagem(ns) não lida(s)',
                                QSystemTrayIcon.MessageIcon.Information,
                                4000,
                            )
                if service.notification_sound:
                    play_sound(service.notification_sound)
        self._save()

    def _pulse_badge(self, item: QListWidgetItem):  # pragma: no cover
        """Animate badge opacity: 1 → 0.4 → 1 twice for visual pop."""
        if not hasattr(self, '_badge_pulse_anim'):
            self._badge_pulse_anim = None
        # Use a viewport opacity flicker (simple approach: schedule 2 repaints)
        vp = self._svc_list.viewport()
        def _repaint():
            vp.update()
        for delay in (80, 160, 240, 320):
            QTimer.singleShot(delay, _repaint)

    def _show_toast(self, service: Service):  # pragma: no cover
        """Show an in-app slide-in toast notification."""
        # Find the right parent: the central widget so toast is positioned correctly
        parent = self.centralWidget() or self
        toast = _ToastNotification(service, parent=parent)
        toast.clicked.connect(self._select_service_by_id)
        toast.show_animated()

    def _on_push_notification(self, service: Service, title: str, body: str):  # pragma: no cover
        """Handle a Web Notification API push from an embedded service."""
        svc_tags = getattr(service, 'tags', [])
        if self._is_dnd_active() or _svc_muted_by_profile(svc_tags):
            return
        add_notification(service.id, service.name, title, body)
        notif_style = self._settings.get('notification_style', 'orbit')
        import time as _time
        if not hasattr(self, '_last_toast_time'):
            self._last_toast_time: dict = {}
        now = _time.monotonic()
        last = self._last_toast_time.get(service.id, 0)
        if now - last > 2.0:  # debounce 2s to avoid badge+push duplicates
            if notif_style in ('orbit', 'both'):
                self._show_toast(service)
                self._last_toast_time[service.id] = now
            if notif_style in ('system', 'both'):
                if hasattr(self, '_tray') and self._tray.isVisible():
                    self._tray.showMessage(
                        f'{service.name}: {title}',
                        body,
                        QSystemTrayIcon.MessageIcon.Information,
                        5000,
                    )
        if service.notification_sound:
            play_sound(service.notification_sound)

    def _fade_switch(self, widget):  # pragma: no cover
        """Fade-in the target widget in the stack with a 150ms animation."""
        if self._stack.currentWidget() is widget:
            return
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b'opacity', widget)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._stack.setCurrentWidget(widget)
        anim.start()
        # Keep reference so GC doesn't collect it
        widget._fade_anim = anim

    def _on_active_load_status(self, status: str):  # pragma: no cover
        self._status_badge.set_status(
            'connecting' if status == 'loading' else
            'ready' if status == 'ready' else
            'error'
        )

    def _update_title(self):  # pragma: no cover
        svc_name = self._active_service.name if self._active_service else ''
        if svc_name:
            self.setWindowTitle(f'{svc_name} — Orbit')
        else:
            self.setWindowTitle('Orbit')

    def _update_title_badge(self):  # pragma: no cover
        total = sum(s.unread for s in self._services)
        if hasattr(self, '_tray'):
            if total > 0:
                self._tray.setToolTip(f'Orbit — {total} não lida(s)')
            else:
                self._tray.setToolTip('Orbit')
        self._update_tray_badge()
        try:
            total = sum(getattr(s, 'unread', 0) for s in self._services)
            hwnd = int(self.winId())
            update_badge(hwnd, total)
        except Exception:
            pass
        self._update_title()

    def _update_tray_badge(self):  # pragma: no cover
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

    def _on_load_status(self, service_id: str, status: str):  # pragma: no cover
        item = self._svc_items.get(service_id)
        if item:
            item.setData(_ROLE_STATUS, status)
            self._svc_list.viewport().update()

    # ── context menu ──────────────────────────────────────────────────────────

    def _show_ctx_menu(self, service: Service, global_pos):  # pragma: no cover
        menu = QMenu(self)
        config_act = menu.addAction('Configurar')
        config_act.setIcon(svg_icon('cog-6-tooth', 14, '#6c7086'))
        add_acc_act = menu.addAction('Adicionar conta')
        add_acc_act.setIcon(svg_icon('plus', 14, '#6c7086'))
        open_win_act = menu.addAction('Abrir em janela')
        open_win_act.setIcon(svg_icon('arrow-top-right-on-square', 14, '#6c7086'))
        pip_act = menu.addAction('Picture-in-Picture')
        pip_act.setIcon(svg_icon('rectangle-stack', 14, '#6c7086'))

        # Enable / Disable service
        menu.addSeparator()
        is_enabled = getattr(service, 'enabled', True)
        toggle_enabled_act = menu.addAction(
            _t('disable_service') if is_enabled else _t('enable_service')
        )
        toggle_enabled_act.triggered.connect(lambda: self._toggle_service_enabled(service))

        is_google = any(t in service.service_type for t in _GOOGLE_TYPES)
        google_login_act = None
        if is_google:
            menu.addSeparator()
            google_login_act = menu.addAction('Como fazer login no Google...')
            google_login_act.setIcon(svg_icon('information-circle', 14, '#89b4fa'))

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
        elif google_login_act and action == google_login_act:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, 'Login no Google — Orbit',
                'Para usar Gmail, Google Meet e outros serviços do Google no Orbit:\n\n'
                '1. Clique na tela do serviço\n'
                '2. Selecione sua conta na tela "Escolha uma conta"\n'
                '3. Caso apareça bloqueio de login, clique em "Usar outra conta" '
                'e conclua o login normalmente\n'
                '4. O Orbit salva a sessão — nas próximas vezes abre direto logado\n\n'
                'ℹ️  Importar cookies do Chrome não funciona mais devido às '
                'proteções de segurança do Google (DBSC) no Chrome 127+.'
            )
        elif action == remove_act:
            self._remove_service(service)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _add_service(self):  # pragma: no cover
        dlg = AddServiceDialog(self)
        if dlg.exec() == QDialog.Accepted:
            svc = dlg.get_service()
            if svc:
                self._services.append(svc)
                self._rebuild_sidebar()
                self._select_service(svc)
                self._save()
                _log_event('service_added', svc.name)

    def _add_account(self):  # pragma: no cover
        if not self._active_service:
            return
        dlg = AddAccountDialog(self._active_service, self)
        if dlg.exec() == QDialog.Accepted:
            acc = dlg.get_account()
            if acc:
                self._active_service.accounts.append(acc)
                self._select_account(acc)
                self._save()

    def _configure(self, service: Service):  # pragma: no cover
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
            _log_event('config_changed', service.name)

    def _remove_service(self, service: Service):  # pragma: no cover
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
        _log_event('service_removed', service.name)

        if self._services:
            self._select_service(self._services[0])

    # ── persistence ───────────────────────────────────────────────────────────

    def _save(self):  # pragma: no cover
        save_workspaces(self._workspaces)

    # ── tray ──────────────────────────────────────────────────────────────────

    def _export_backup(self):  # pragma: no cover
        import zipfile
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, 'Exportar configurações', 'orbit-backup.zip',
            'ZIP Files (*.zip)'
        )
        if not path:
            return
        from .storage import STORAGE_DIR
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in ['workspaces.json', 'settings.json']:
                fpath = os.path.join(STORAGE_DIR, fname)
                if os.path.exists(fpath):
                    zf.write(fpath, fname)
        ToastManager.show(self, 'Backup exportado com sucesso!', 'success')

    def _import_backup(self):  # pragma: no cover
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

    def _toggle_notif_center(self):  # pragma: no cover
        if hasattr(self, '_notif_center'):
            self._notif_center.toggle()

    def _on_service_status_changed(self, svc_id: str, status: str):  # pragma: no cover
        item = self._svc_items.get(svc_id)
        if item:
            item.setData(_ROLE_STATUS, status)
            self._svc_list.viewport().update()

    def _get_accent_color(self) -> str:  # pragma: no cover
        ws = getattr(self, '_active_workspace', None)
        if ws and ws.accent:
            return ws.accent
        return ACCENTS.get(getattr(self, '_accent', 'Iris'), ACCENTS['Iris'])

    def _show_webdav_dialog(self):  # pragma: no cover
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                                        QPushButton, QLabel, QHBoxLayout, QDialogButtonBox)
        from .webdav_sync import get_webdav, save_webdav_config, load_webdav_config
        cfg = load_webdav_config()
        dlg = QDialog(self)
        dlg.setWindowTitle('🗄️ WebDAV / OneDrive Sync')
        dlg.setMinimumWidth(460)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel('🗄️ Sincronização WebDAV')
        title.setStyleSheet('font-size:15px; font-weight:bold;')
        layout.addWidget(title)

        hint = QLabel(
            'Configure o servidor WebDAV para fazer backup automático.<br>'
            'Compatível com Nextcloud, ownCloud, OneDrive (WebDAV), etc.'
        )
        hint.setWordWrap(True)
        hint.setStyleSheet('font-size:11px; color:#6c7086;')
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        url_edit = QLineEdit(cfg.get('url', ''))
        url_edit.setPlaceholderText('https://seu-servidor/webdav/')
        form.addRow('URL WebDAV', url_edit)
        user_edit = QLineEdit(cfg.get('username', ''))
        user_edit.setPlaceholderText('usuário')
        form.addRow('Usuário', user_edit)
        pass_edit = QLineEdit(cfg.get('password', ''))
        pass_edit.setPlaceholderText('senha')
        pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Senha', pass_edit)
        layout.addLayout(form)

        status_lbl = QLabel('')
        status_lbl.setWordWrap(True)
        status_lbl.setStyleSheet('font-size:12px;')
        layout.addWidget(status_lbl)

        btn_row = QHBoxLayout()
        test_btn = QPushButton('🔌 Testar conexão')
        test_btn.setObjectName('secondaryButton')
        upload_btn = QPushButton('☁️ Fazer backup agora')
        upload_btn.setObjectName('primaryButton')
        btn_row.addWidget(test_btn)
        btn_row.addWidget(upload_btn)
        layout.addLayout(btn_row)

        close_btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btns.rejected.connect(dlg.reject)
        layout.addWidget(close_btns)

        def save_and_test():
            url = url_edit.text().strip()
            user = user_edit.text().strip()
            pw = pass_edit.text()
            if not url:
                status_lbl.setText('⚠ URL é obrigatória.')
                return
            save_webdav_config(url, user, pw)
            wd = get_webdav()
            wd.configure(url, user, pw)
            status_lbl.setText('⏳ Testando...')
            dlg.repaint()
            ok, msg = wd.test_connection()
            status_lbl.setText(f'{"✅" if ok else "❌"} {msg}')

        def do_backup():
            url = url_edit.text().strip()
            user = user_edit.text().strip()
            pw = pass_edit.text()
            if not url:
                status_lbl.setText('⚠ URL é obrigatória.')
                return
            save_webdav_config(url, user, pw)
            wd = get_webdav()
            wd.configure(url, user, pw)
            import json as _json
            from .storage import load_settings as _ls
            backup_data = _json.dumps({'settings': _ls()}).encode('utf-8')
            fname = wd.backup_filename()
            status_lbl.setText('⏳ Enviando...')
            dlg.repaint()
            ok = wd.upload_data(fname, backup_data)
            status_lbl.setText('✅ Backup enviado!' if ok else '❌ Falha ao enviar backup.')

        test_btn.clicked.connect(save_and_test)
        upload_btn.clicked.connect(do_backup)
        dlg.exec()

    def _show_cloud_sync_dialog(self):  # pragma: no cover
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
                    import json as _json
                    import os as _os
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

    def _show_import_dialog(self):  # pragma: no cover
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

    def _show_stats_dialog(self):  # pragma: no cover
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

    def _show_shortcuts_dialog(self):  # pragma: no cover
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

    def _setup_tray(self):  # pragma: no cover
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'icon.ico')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        )
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip('Orbit')

        tray_menu = QMenu()

        # Primary actions
        show_act = tray_menu.addAction('Mostrar Orbit')
        show_act.triggered.connect(self._show_and_raise)
        tray_menu.addSeparator()

        # Lock
        lock_act = tray_menu.addAction('Bloquear agora')
        lock_act.setIcon(svg_icon('lock-closed', 14, '#6c7086'))
        lock_act.triggered.connect(self._lock_now)
        tray_menu.addSeparator()

        # Privacy & focus
        self._tray_privacy_act = tray_menu.addAction('Modo Privacidade')
        self._tray_privacy_act.setIcon(svg_icon('eye-slash', 14, '#6c7086'))
        self._tray_privacy_act.setCheckable(True)
        self._tray_privacy_act.setChecked(self._privacy_mode)
        self._tray_privacy_act.triggered.connect(self._toggle_privacy_mode)

        from PySide6.QtGui import QActionGroup

        # Focus profile submenu
        focus_menu = tray_menu.addMenu(f'🎯 {_t("focus_profile")}')
        profile_group = QActionGroup(focus_menu)
        profile_group.setExclusive(True)
        self._tray_profile_actions: dict = {}
        active_profile = _get_focus_profile()
        for p_key in _PROFILE_ORDER:
            p_label = _PROFILE_LABELS.get(p_key, p_key)
            p_act = focus_menu.addAction(p_label)
            p_act.setCheckable(True)
            p_act.setChecked(p_key == active_profile)
            p_act.triggered.connect(lambda _, pk=p_key: self._set_focus_profile(pk))
            profile_group.addAction(p_act)
            self._tray_profile_actions[p_key] = p_act

        # DND submenu
        dnd_menu = tray_menu.addMenu('Não perturbe')
        dnd_menu.setIcon(svg_icon('bell-slash', 14, '#6c7086'))
        self._tray_dnd_menu = dnd_menu
        self._build_dnd_menu(dnd_menu)

        tray_menu.addSeparator()

        # Tools
        stats_act = tray_menu.addAction('Estatísticas')
        stats_act.setIcon(svg_icon('chart-bar', 14, '#6c7086'))
        stats_act.triggered.connect(self._show_stats_dialog)
        shortcuts_act = tray_menu.addAction('Atalhos')
        shortcuts_act.setIcon(svg_icon('command-line', 14, '#6c7086'))
        shortcuts_act.triggered.connect(self._show_shortcuts_dialog)
        reading_list_act = tray_menu.addAction('Lista de Leitura')
        reading_list_act.triggered.connect(self._show_reading_list)
        ws_schedule_act = tray_menu.addAction('Agendamento de Workspace')
        ws_schedule_act.triggered.connect(self._show_workspace_schedule)
        audit_act = tray_menu.addAction(_t('view_audit_log'))
        audit_act.triggered.connect(self._show_audit_log)

        tray_menu.addSeparator()

        # Backup (kept in tray for quick access)
        backup_menu = tray_menu.addMenu('Backup')
        backup_menu.setIcon(svg_icon('archive-box-arrow-down', 14, '#6c7086'))
        export_act = backup_menu.addAction('Exportar configurações')
        export_act.setIcon(svg_icon('arrow-up-tray', 14, '#6c7086'))
        export_act.triggered.connect(self._export_backup)
        import_act = backup_menu.addAction('Importar configurações')
        import_act.setIcon(svg_icon('arrow-down-tray', 14, '#6c7086'))
        import_act.triggered.connect(self._import_backup)

        tray_menu.addSeparator()

        # Settings + Quit
        settings_act = tray_menu.addAction('Configurações...')
        settings_act.setIcon(svg_icon('cog-6-tooth', 14, '#6c7086'))
        settings_act.triggered.connect(self._show_settings)
        tray_menu.addSeparator()
        quit_act = tray_menu.addAction('Fechar Orbit')
        quit_act.triggered.connect(QApplication.instance().quit)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(
            lambda reason: self._show_and_raise()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        if load_settings().get('show_tray', True):
            self._tray.show()

    def _setup_global_hotkey(self):  # pragma: no cover
        """Register Ctrl+Shift+O as a global hotkey to bring Orbit to front (Windows only)."""
        if sys.platform != 'win32':
            return
        try:
            import ctypes
            from ctypes import wintypes
            from threading import Thread

            MOD_CTRL_SHIFT = 0x0002 | 0x0004  # MOD_CONTROL | MOD_SHIFT
            VK_O = 0x4F
            HOTKEY_ID = 1

            def _hotkey_listener():
                user32 = ctypes.windll.user32
                if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CTRL_SHIFT, VK_O):
                    return
                msg = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312:  # WM_HOTKEY
                        QTimer.singleShot(0, self._show_and_raise)

            t = Thread(target=_hotkey_listener, daemon=True)
            t.start()
        except Exception:
            pass

    def _show_and_raise(self):  # pragma: no cover
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_ad_block(self, enabled: bool):  # pragma: no cover
        set_ad_block(enabled)
        settings = load_settings()
        settings['ad_block'] = enabled
        save_settings(settings)

    # ── DND ───────────────────────────────────────────────────────────────────

    def _is_dnd_active(self) -> bool:
        if self._dnd_until is not None and time.time() < self._dnd_until:
            return True
        return is_quiet_now(load_settings())

    def _set_dnd(self, minutes: Optional[int]):  # pragma: no cover
        if minutes is None:
            self._dnd_until = None
        else:
            self._dnd_until = time.time() + minutes * 60
        self._update_dnd_ui()

    def _toggle_dnd_shortcut(self):  # pragma: no cover
        if self._is_dnd_active():
            self._set_dnd(None)
        else:
            self._set_dnd(60)

    def _update_dnd_ui(self):  # pragma: no cover
        if self._active_service:
            self._refresh_header()

    def _build_dnd_menu(self, menu: QMenu):  # pragma: no cover
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
        next_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if next_8am <= now:
            next_8am += datetime.timedelta(days=1)
        return max(1, int((next_8am - now).total_seconds() / 60))

    def _show_dnd_menu(self):  # pragma: no cover
        menu = QMenu(self)
        self._build_dnd_menu(menu)
        btn = self.sender()
        if btn:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        else:
            menu.exec(self.cursor().pos())

    def _show_quiet_hours_dialog(self):  # pragma: no cover
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
                                        QTimeEdit, QDialogButtonBox, QLabel, QGroupBox)
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

    def _show_notif_history_panel(self):  # pragma: no cover
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

    def _quick_switch(self):  # pragma: no cover
        if len(self._recent_services) < 2:
            return
        prev_id = self._recent_services[1]
        svc = next((s for s in self._services if s.id == prev_id), None)
        if svc:
            self._select_service(svc)

    def _select_service_by_id(self, svc_id: str):  # pragma: no cover
        svc = next((s for s in self._services if s.id == svc_id), None)
        if svc:
            self._select_service(svc)

    # ── multi-window ──────────────────────────────────────────────────────────

    def _open_in_window(self, service: Service, account: Account):  # pragma: no cover
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

    def _open_pip(self, service: Service, account: Account):  # pragma: no cover
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
        tb_lbl = QLabel(f'⬤ {service.name}')
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

    def _popout_service(self, svc: Service):  # pragma: no cover
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

    def _check_workspace_schedule(self):  # pragma: no cover
        from .workspace_schedule import get_active_workspace_id
        ws_id = get_active_workspace_id(self._ws_schedule, self._workspaces)
        if ws_id and ws_id != self._active_workspace.id:
            target = next((w for w in self._workspaces if w.id == ws_id), None)
            if target:
                self._switch_workspace(target)
                ToastManager.show(self, f'Workspace trocado: {target.name}', 'info')

    def _show_workspace_schedule(self):  # pragma: no cover
        from .workspace_schedule import load_schedule
        from .dialogs import WorkspaceScheduleDialog
        self._ws_schedule = load_schedule()
        dlg = WorkspaceScheduleDialog(self._workspaces, self._ws_schedule, self)
        if dlg.exec():
            self._ws_schedule = load_schedule()

    # ── reading list ──────────────────────────────────────────────────────────

    def _show_reading_list(self):  # pragma: no cover
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

    def _register_url_scheme(self):  # pragma: no cover
        """Register orbit:// URL scheme in Windows registry."""
        try:
            import winreg
            import sys
            exe = sys.executable
            key_path = r'Software\Classes\Orbit'
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'URL:Orbit Protocol')
                winreg.SetValueEx(key, 'URL Protocol', 0, winreg.REG_SZ, '')
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r'\shell\open\command') as key:
                winreg.SetValueEx(key, '', 0, winreg.REG_SZ, f'"{exe}" "%1"')
        except Exception:
            pass  # Non-fatal

    # ── general settings ──────────────────────────────────────────────────────

    def _show_settings(self):  # pragma: no cover
        """Open the General Settings dialog (Ctrl+,)."""
        from .dialogs import GeneralSettingsDialog
        dlg = GeneralSettingsDialog(
            callbacks={
                'apply_theme':       self._apply_theme,
                'set_accent':        self._set_accent,
                'set_startup':       self._set_startup,
                'is_startup_enabled': self._is_startup_enabled,
                'show_pin_config':   self._show_pin_config_dialog,
                'show_encrypt_config': self._show_encrypt_config_dialog,
                'check_updates':     lambda: self._check_updates(silent=False),
                'show_cloud_sync':   self._show_cloud_sync_dialog,
                'show_webdav':       self._show_webdav_dialog,
                'show_import':       self._show_import_dialog,
                'set_ad_block':      self._toggle_ad_block,
                'apply_sidebar_widths': self._apply_sidebar_widths,
                'apply_sidebar_style':    self._apply_sidebar_style,
                'apply_sidebar_opacity':  self._apply_sidebar_opacity,
                'apply_sidebar_custom_bg': self._apply_sidebar_custom_bg,
                'apply_sidebar_custom_border': self._apply_sidebar_custom_border,
                'apply_sidebar_position': self._apply_sidebar_position,
                'apply_tray_settings':  self._apply_tray_settings,
                'apply_workspace_enabled': self.set_workspaces_enabled,
            },
            parent=self,
        )
        dlg.exec()

    def _apply_sidebar_style(self, style: str):  # pragma: no cover
        """Switch sidebar visual style."""
        self._sidebar_style = style
        self._svc_delegate.style = style
        self._glass_sidebar.style = style
        self._glass_sidebar.update()
        settings = load_settings()
        settings['sidebar_style'] = style
        save_settings(settings)
        self._rebuild_sidebar()

    def _apply_sidebar_opacity(self, value: int):  # pragma: no cover
        self._glass_sidebar.opacity = value
        self._glass_sidebar.update()
        settings = load_settings()
        settings['sidebar_opacity'] = value
        save_settings(settings)

    def _apply_sidebar_custom_bg(self, color: str):  # pragma: no cover
        self._glass_sidebar.custom_bg = color
        self._glass_sidebar.update()
        settings = load_settings()
        settings['sidebar_custom_bg'] = color
        save_settings(settings)

    def _apply_sidebar_custom_border(self, color: str):  # pragma: no cover
        self._glass_sidebar.custom_border = color
        self._glass_sidebar.update()
        settings = load_settings()
        settings['sidebar_custom_border'] = color
        save_settings(settings)

    def _apply_sidebar_position(self, position: str):  # pragma: no cover
        self._sidebar_position = position
        settings = load_settings()
        settings['sidebar_position'] = position
        save_settings(settings)
        from .toast import ToastManager
        ToastManager.show(self, 'Posição alterada. Reinicie o app para aplicar.', 'info', 4000)

    def _apply_sidebar_widths(self, compact_w: int, expanded_w: int):  # pragma: no cover
        """Apply new sidebar widths from settings without requiring restart."""
        target_w = compact_w if self._sidebar_compact else expanded_w
        total = sum(self._splitter.sizes())
        self._splitter.setSizes([target_w, total - target_w, 0])

    def _apply_tray_settings(self, show_tray: bool):  # pragma: no cover
        """Show or hide the system tray icon based on settings."""
        if hasattr(self, '_tray'):
            if show_tray:
                self._tray.show()
            else:
                self._tray.hide()

    def _create_view_only(self, service, account) -> 'ServiceView':  # pragma: no cover
        """Create a ServiceView in the background without switching the visible service.

        Unlike _select_account(), this method does NOT call _fade_switch() or alter the
        active service/account state — safe to call during preload.
        """
        from PySide6.QtNetwork import QNetworkProxy
        key = (service.id, account.id)
        if key in self._views:
            return self._views[key]
        # Apply proxy (same logic as _select_account)
        proxy_str = getattr(service, 'proxy', '')
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
        view = ServiceView(account.profile_name, account.url,
                           service_type=service.service_type,
                           custom_css=service.custom_css,
                           custom_js=service.custom_js,
                           zoom=service.zoom,
                           incognito=getattr(service, 'incognito', False),
                           spellcheck=getattr(service, 'spellcheck', True))
        view.badge_changed.connect(
            lambda count, svc=service: self._update_badge(svc, count)
        )
        view.notification_received.connect(
            lambda title, body, svc=service: self._on_push_notification(svc, title, body)
        )
        view.load_status_changed.connect(
            lambda s, sid=service.id: self._on_load_status(sid, s)
        )
        self._views[key] = view
        self._loaded_services.add(service.id)
        self._stack.addWidget(view)
        return view

    def _schedule_service_preload(self, services: list) -> None:  # pragma: no cover
        """Pre-warm service WebViews in the background after startup, one every 800 ms.

        Uses _create_view_only() so the currently visible service is never displaced.
        """
        def _load_next(remaining):
            if not remaining:
                return
            svc = remaining[0]
            rest = remaining[1:]
            ha = getattr(svc, 'hibernate_after', None)
            if svc.accounts and ha != 0:
                key = (svc.id, svc.accounts[0].id)
                if key not in self._views:
                    self._create_view_only(svc, svc.accounts[0])
            QTimer.singleShot(800, lambda: _load_next(rest))

        QTimer.singleShot(2000, lambda: _load_next(services))

    def _check_updates(self, silent: bool = False):  # pragma: no cover
        from .updater import check_for_update
        import threading

        def run():
            has_update, latest, url, _dl = check_for_update()
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

    def _init_encryption(self):  # pragma: no cover
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

    def _show_encrypt_config_dialog(self):  # pragma: no cover
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

    def _lock_now(self):  # pragma: no cover
        settings = load_settings()
        pin_hash = settings.get('pin_hash')
        if not pin_hash:
            return
        if not self._lock_screen:
            self._lock_screen = LockScreen(pin_hash, self)
            self._lock_screen.unlocked.connect(self._lock_screen.hide)
            self._lock_screen.unlocked.connect(lambda: _log_event('unlocked', 'pin'))
        else:
            self._lock_screen._pin_hash = pin_hash
        self._lock_screen.reset()
        self._lock_screen.setGeometry(self.rect())
        self._lock_screen.show()
        self._lock_screen.raise_()
        _log_event('locked')

    def _show_shortcuts(self):  # pragma: no cover
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

    def _check_auto_lock(self):  # pragma: no cover
        settings = load_settings()
        minutes = settings.get('auto_lock_minutes', 0)
        if minutes <= 0 or not settings.get('pin_hash'):
            return
        if hasattr(self, '_lock_screen') and self._lock_screen and self._lock_screen.isVisible():
            return
        if time.time() - self._last_activity > minutes * 60:
            self._lock_now()
            self._last_activity = time.time()

    def _show_pin_config_dialog(self):  # pragma: no cover
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

    def _show_onboarding(self):  # pragma: no cover
        dlg = OnboardingDialog(self)
        dlg.theme_chosen.connect(self._apply_theme)
        dlg.service_chosen.connect(lambda st: self._quick_add_service(st))
        dlg.exec()
        s = load_settings()
        s['onboarding_done'] = True
        save_settings(s)

    def _quick_add_service(self, service_type: str):  # pragma: no cover
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
            custom_css=entry.custom_css or '',
            accounts=[Account(id=acc_id, label=entry.name, url=url,
                              profile_name=profile_name, authuser=0)],
        )
        self._services.append(svc)
        self._rebuild_sidebar()
        self._select_service(svc)
        self._save()

    def closeEvent(self, event):  # pragma: no cover
        g = self.geometry()
        settings = load_settings()
        settings['geometry'] = {'x': g.x(), 'y': g.y(), 'w': g.width(), 'h': g.height()}
        save_settings(settings)

        # Stop timers to prevent leaks
        if hasattr(self, '_svc_delegate') and self._svc_delegate._hover_timer.isActive():
            self._svc_delegate._hover_timer.stop()
        if hasattr(self, '_rebuild_timer'):
            self._rebuild_timer.stop()
        if hasattr(self, '_schedule_timer'):
            self._schedule_timer.stop()
        for t in getattr(self, '_hibernate_timers', {}).values():
            t.stop()
        # Disconnect view signals
        for view in getattr(self, '_views', {}).values():
            try:
                view.badge_changed.disconnect()
                view.load_status_changed.disconnect()
                view.notification_received.disconnect()
            except RuntimeError:
                pass

        if settings.get('minimize_to_tray', False):
            event.ignore()
            self.hide()
            if hasattr(self, '_tray') and self._tray.isVisible():
                self._tray.showMessage(
                    'Orbit',
                    'Orbit continua rodando em segundo plano. Clique no ícone da bandeja para restaurar.',
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )
        else:
            event.accept()
            QApplication.instance().quit()

    # ── hibernate ─────────────────────────────────────────────────────────────

    def _setup_hibernate_timers(self):  # pragma: no cover
        """Start/restart hibernate timer for all services that have it configured."""
        for svc in self._services:
            self._reset_hibernate_timer(svc)

    def _reset_hibernate_timer(self, service: Service):  # pragma: no cover
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

    def _hibernate_service(self, service: Service):  # pragma: no cover
        """Pause all views for a service (load blank page to free memory)."""
        from PySide6.QtCore import QUrl
        for acc in service.accounts:
            key = (service.id, acc.id)
            if key in self._views:
                self._views[key].load(QUrl('about:blank'))
                self._hibernated.add(key)
        print(f'[hibernate] {service.name} hibernated')

    def _wake_service(self, service: Service, account: Account):  # pragma: no cover
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
        if sys.platform != 'win32':
            return False
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._STARTUP_KEY)
            winreg.QueryValueEx(key, self._STARTUP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _set_startup(self, enable: bool):
        if sys.platform != 'win32':
            return
        try:
            import winreg
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

    def _show_palette(self):  # pragma: no cover
        from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

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

    # ── sidebar list signals ──────────────────────────────────────────────────

    def _on_svc_item_clicked(self, item: QListWidgetItem):  # pragma: no cover
        svc = item.data(_ROLE_SVC)
        if svc and getattr(svc, 'enabled', True):
            self._select_service(svc)

    def _on_svc_ctx_menu(self, pos):  # pragma: no cover
        item = self._svc_list.itemAt(pos)
        if not item:
            return
        svc = item.data(_ROLE_SVC)
        if svc:
            self._show_ctx_menu(svc, self._svc_list.viewport().mapToGlobal(pos))

    def _on_svc_item_entered(self, item: QListWidgetItem):  # pragma: no cover
        pass  # Badge already shows the count — no extra tooltip needed

    _ALLOWED_URL_COMMANDS = {'open', 'service', 'workspace'}

    def handle_url_scheme(self, url: str):
        """Handle an orbit:// URL passed via command-line or protocol activation.

        Supported URLs:
          orbit://open                  — bring window to front
          orbit://service/<service_id>  — switch to a service by ID
          orbit://workspace/<name>      — switch to a workspace by name
        """
        if not isinstance(url, str) or not url.startswith('orbit://'):
            return
        # Sanitize: limit length, strip dangerous chars
        url = url[:256]

        self.show()
        self.raise_()
        self.activateWindow()

        try:
            path = url[len('orbit://'):]
            parts = [p for p in path.split('/') if p]
            if not parts:
                return
            command = parts[0].lower()
            if command not in self._ALLOWED_URL_COMMANDS:
                return
            if command == 'service' and len(parts) >= 2:
                service_id = parts[1][:128]  # limit param length
                for svc in self._services:
                    if svc.id == service_id:
                        self._select_service(svc)
                        break
            elif command == 'workspace' and len(parts) >= 2:
                ws_name = parts[1][:128].lower()
                for ws in self._workspaces:
                    if ws.name.lower() == ws_name:
                        self._switch_workspace(ws)
                        break
        except Exception:
            pass


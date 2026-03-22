"""Centralized theme and color token system for Orbit."""
from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import Literal

if sys.platform == 'win32':
    import winreg  # type: ignore[import]

ThemeMode = Literal['dark', 'light', 'system']

# ── Accent palettes ───────────────────────────────────────────────────────────
ACCENTS: dict[str, str] = {
    'Iris':  '#7c6af7',   # purple — default
    'Ocean': '#007acc',   # blue
    'Sage':  '#52a97f',   # green
    'Coral': '#e8735a',   # orange-red
    'Rose':  '#f472b6',   # pink
    'Gold':  '#d4a843',   # amber
}

def _darken(hex_color: str, pct: int = 18) -> str:
    """Darken a hex color by reducing brightness by pct%."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    factor = (100 - pct) / 100
    r, g, b = int(r*factor), int(g*factor), int(b*factor)
    return f'#{r:02x}{g:02x}{b:02x}'

def _alpha(hex_color: str, alpha_pct: int) -> str:
    """Return rgba() string with given alpha percentage."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    a = round(alpha_pct / 100 * 255)
    return f'rgba({r},{g},{b},{a})'

def _is_system_dark() -> bool:
    if sys.platform != 'win32':
        return True
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
        val, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        return val == 0
    except Exception:
        return True

@dataclass
class ColorTokens:
    # Backgrounds
    bg_base: str
    bg_surface: str
    bg_elevated: str
    bg_hover: str
    # Foregrounds
    fg_primary: str
    fg_muted: str
    fg_subtle: str
    # Border
    border: str
    # Accent (dynamic)
    accent: str
    accent_hover: str
    accent_dim: str
    accent_muted: str

    def qss(self) -> str:
        """Generate QSS stylesheet with all tokens."""
        return _build_qss(self)

def dark_tokens(accent: str) -> ColorTokens:
    return ColorTokens(
        bg_base='#16161a',
        bg_surface='#1c1c23',
        bg_elevated='#242430',
        bg_hover='#2a2a3a',
        fg_primary='#e8e8f0',
        fg_muted='#6e6e8a',
        fg_subtle='#3e3e52',
        border='#2e2e3d',
        accent=accent,
        accent_hover=_darken(accent, 15),
        accent_dim=_alpha(accent, 28),
        accent_muted=_alpha(accent, 18),
    )

def light_tokens(accent: str) -> ColorTokens:
    return ColorTokens(
        bg_base='#f4f4f8',
        bg_surface='#ffffff',
        bg_elevated='#ebebf2',
        bg_hover='#e0e0ec',
        fg_primary='#1a1a2e',
        fg_muted='#6b6b80',
        fg_subtle='#b0b0c0',
        border='#d0d0dc',
        accent=accent,
        accent_hover=_darken(accent, 15),
        accent_dim=_alpha(accent, 22),
        accent_muted=_alpha(accent, 14),
    )

def get_tokens(mode: ThemeMode, accent: str) -> ColorTokens:
    is_dark = mode == 'dark' or (mode == 'system' and _is_system_dark())
    return dark_tokens(accent) if is_dark else light_tokens(accent)

def _build_qss(t: ColorTokens) -> str:
    return f"""
/* ── Base ── */
* {{
    font-family: 'Inter', 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    color: {t.fg_primary};
    outline: none;
}}
QWidget {{
    background-color: {t.bg_base};
    color: {t.fg_primary};
}}
QMainWindow, QDialog {{
    background-color: {t.bg_base};
}}

/* ── Sidebar ── */
#sidebar {{
    background: {t.bg_surface};
    border-right: 1px solid {t.border};
    min-width: 64px;
}}

/* ── Header ── */
#header {{
    background-color: {t.bg_surface};
    border-bottom: 1px solid {t.border};
    min-height: 40px;
    max-height: 40px;
}}

/* ── Stack / Content ── */
#stack {{
    background-color: {t.bg_base};
}}

/* ── Service Buttons (sidebar) ── */
#svcBtn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 6px 8px;
    color: {t.fg_muted};
}}
#svcBtn:hover {{
    background-color: {t.bg_hover};
    color: {t.fg_primary};
}}
#svcBtn[active="true"] {{
    background-color: {t.accent_dim};
    color: {t.accent};
    font-weight: bold;
    border-left: 3px solid {t.accent};
    padding-left: 5px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {t.bg_elevated};
    color: {t.fg_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 14px;
    min-height: 22px;
}}
QPushButton:hover {{
    background-color: {t.bg_hover};
    border-color: {t.accent};
}}
QPushButton:pressed {{
    background-color: {t.accent_dim};
    border-color: {t.accent};
}}
QPushButton:disabled {{
    color: {t.fg_subtle};
    background-color: {t.bg_elevated};
    border-color: {t.border};
}}
QPushButton#primaryButton {{
    background-color: {t.accent};
    color: #ffffff;
    border: none;
    font-weight: bold;
}}
QPushButton#primaryButton:hover {{
    background-color: {t.accent_hover};
}}
QPushButton#primaryButton:pressed {{
    background-color: {t.accent_hover};
    opacity: 0.9;
}}
QPushButton#iconBtn, QPushButton#headerBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
}}
QPushButton#iconBtn:hover, QPushButton#headerBtn:hover {{
    background-color: {t.bg_hover};
}}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {t.bg_elevated};
    color: {t.fg_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 10px;
    selection-background-color: {t.accent_dim};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {t.accent};
    background-color: {t.bg_surface};
}}
QLineEdit:disabled {{
    color: {t.fg_muted};
    background-color: {t.bg_surface};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {t.bg_elevated};
    color: {t.fg_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 22px;
}}
QComboBox:focus {{
    border-color: {t.accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {t.bg_elevated};
    border: 1px solid {t.border};
    border-radius: 6px;
    selection-background-color: {t.accent_dim};
    color: {t.fg_primary};
}}

/* ── SpinBox / TimeEdit ── */
QSpinBox, QTimeEdit, QDateEdit {{
    background-color: {t.bg_elevated};
    color: {t.fg_primary};
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 4px 8px;
}}
QSpinBox:focus, QTimeEdit:focus {{
    border-color: {t.accent};
}}

/* ── CheckBox / RadioButton ── */
QCheckBox, QRadioButton {{
    color: {t.fg_primary};
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1.5px solid {t.border};
    border-radius: 3px;
    background-color: {t.bg_elevated};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}
QRadioButton::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {t.accent};
}}

/* ── Labels ── */
QLabel {{
    background-color: transparent;
    color: {t.fg_primary};
}}
QLabel#wTitle {{
    font-size: 22px;
    font-weight: 700;
    color: {t.fg_primary};
}}
QLabel#wSub {{
    font-size: 13px;
    color: {t.fg_muted};
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {t.border};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    color: {t.fg_muted};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.5px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {t.accent};
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-radius: 0 8px 8px 8px;
    background-color: {t.bg_surface};
}}
QTabBar::tab {{
    background-color: transparent;
    color: {t.fg_muted};
    padding: 7px 18px;
    border-bottom: 2px solid transparent;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    color: {t.fg_primary};
    border-bottom: 3px solid {t.accent};
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: {t.bg_hover};
    border-radius: 4px 4px 0 0;
}}

/* ── Lists ── */
QListWidget {{
    background-color: {t.bg_surface};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-radius: 4px;
    color: {t.fg_primary};
}}
QListWidget::item:selected {{
    background-color: {t.accent_dim};
    color: {t.accent};
    border-left: 2px solid {t.accent};
}}
QListWidget::item:hover:!selected {{
    background-color: {t.bg_hover};
}}

/* ── Menus ── */
QMenu {{
    background-color: {t.bg_elevated};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
    color: {t.fg_primary};
}}
QMenu::item:selected {{
    background-color: {t.accent_dim};
    color: {t.fg_primary};
}}
QMenu::item:disabled {{
    color: {t.fg_subtle};
}}
QMenu::separator {{
    height: 1px;
    background: {t.border};
    margin: 4px 8px;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {t.fg_subtle};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {t.fg_muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {t.fg_subtle};
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {t.fg_muted};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {t.border};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {t.bg_elevated};
    border: 1px solid {t.border};
    border-radius: 6px;
    min-height: 8px;
    max-height: 14px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {t.accent};
    border-radius: 5px;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {t.bg_elevated};
    color: {t.fg_primary};
    border: 1px solid {t.accent_muted};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
}}

/* ── StackedWidget / Welcome ── */
#welcome {{
    background-color: {t.bg_base};
}}

/* ── Workspace button ── */
#workspaceBtn {{
    background-color: transparent;
    border: 1px solid {t.border};
    border-radius: 6px;
    padding: 4px 8px;
    color: {t.fg_muted};
    font-size: 11px;
    text-align: left;
    max-width: 100%;
    text-overflow: ellipsis;
}}
#workspaceBtn:hover {{
    background-color: {t.bg_hover};
    color: {t.fg_primary};
    border-color: {t.accent};
}}

/* ── Sidebar workspace / add buttons ── */
#wsBtn {{
    background: transparent;
    color: {t.fg_muted};
    border: none;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    padding: 0 8px;
    text-align: left;
    min-width: 0;
    max-width: 100%;
}}
#wsBtn:hover {{
    background: {t.bg_hover};
    color: {t.fg_primary};
}}
#addBtn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {t.fg_muted};
}}
#addBtn:hover {{
    background: {t.bg_hover};
    color: {t.fg_primary};
}}

/* ── Group headers (sidebar) ── */
#groupHeader {{
    background-color: transparent;
    border: none;
    color: {t.fg_muted};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 0.8px;
    padding: 4px 8px;
    text-align: left;
}}
#groupHeader:hover {{
    color: {t.fg_primary};
}}

/* ── Service Cards (dashboard) ── */
QFrame#serviceCard {{
    background-color: {t.bg_surface};
    border: 1px solid {t.border};
    border-radius: 10px;
}}
QFrame#serviceCard:hover {{
    border-color: {t.accent};
    background-color: {t.bg_elevated};
}}

/* ── Theme Cards (onboarding) ── */
QFrame#themeCard {{
    background-color: {t.bg_elevated};
    border: 1px solid {t.border};
    border-radius: 8px;
}}

/* ── Lock screen ── */
#lockScreen {{
    background-color: {t.bg_base};
}}

/* ── Dialogs ── */
QDialog {{
    background-color: {t.bg_base};
    border: 1px solid {t.border};
    border-radius: 8px;
}}

/* ── AI Sidebar ── */
#aiSidebar {{
    background-color: {t.bg_surface};
    border-left: 1px solid {t.border};
}}
#aiHeader {{
    background-color: {t.bg_elevated};
    border-bottom: 1px solid {t.border};
}}
"""

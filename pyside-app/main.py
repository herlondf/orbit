"""
Orbit — entry point
"""
import os
import sys
from typing import Optional

# Chromium flags — must be set before QApplication is created
# --disable-blink-features=AutomationControlled removes navigator.webdriver
# --no-first-run suppresses Chrome's first-run dialogs inside WebEngine
_chromium_flags = ' '.join([
    '--disable-blink-features=AutomationControlled',
    '--no-first-run',
    '--disable-features=IsolateOrigins',
    '--disable-site-isolation-trials',
    '--disable-gpu-shader-disk-cache',   # prevents cache migration errors on startup
])
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = _chromium_flags

# Must be imported before QApplication when using QtWebEngine
from PySide6.QtCore import Qt, QCoreApplication

# Required for WebEngine + multiple GL contexts
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from pathlib import Path

from app.window import OrbitWindow


def _load_fonts():
    fonts_dir = Path(__file__).parent / 'assets' / 'fonts'
    for ttf in fonts_dir.glob('*.ttf'):
        QFontDatabase.addApplicationFont(str(ttf))


def _parse_url_scheme(args: list) -> Optional[str]:
    """Parse orbit:// URL from command-line arguments."""
    for arg in args:
        if arg.startswith('orbit://'):
            return arg
    return None


def _show_splash(app: QApplication) -> 'QSplashScreen':
    from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
    from PySide6.QtCore import Qt, QRect
    from PySide6.QtWidgets import QSplashScreen

    px = QPixmap(480, 300)
    px.fill(QColor('#16161a'))
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, 480, 300)
    grad.setColorAt(0, QColor('#1c1c23'))
    grad.setColorAt(1, QColor('#16161a'))
    p.fillRect(0, 0, 480, 300, grad)

    p.setFont(QFont('Segoe UI Emoji', 48))
    p.setPen(QColor('#e8e8f0'))
    p.drawText(QRect(0, 60, 480, 80), Qt.AlignCenter, '🐙')

    p.setFont(QFont('Inter', 26, QFont.Bold))
    p.setPen(QColor('#e8e8f0'))
    p.drawText(QRect(0, 150, 480, 50), Qt.AlignCenter, 'Orbit')

    p.setFont(QFont('Inter', 11))
    p.setPen(QColor('#6c7086'))
    p.drawText(QRect(0, 198, 480, 30), Qt.AlignCenter, 'Your unified workspace')

    p.end()

    splash = QSplashScreen(px)
    splash.show()
    app.processEvents()
    return splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Orbit')
    app.setOrganizationName('Orbit')
    app.setQuitOnLastWindowClosed(False)

    _load_fonts()

    font = QFont('Inter', 10)
    app.setFont(font)

    splash = _show_splash(app)

    win = OrbitWindow()
    win.show()
    splash.finish(win)

    url = _parse_url_scheme(sys.argv[1:])
    if url:
        win.handle_url_scheme(url)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

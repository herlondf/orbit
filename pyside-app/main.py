"""
Orbit — entry point
"""
import os
import sys
from typing import Optional

# ── Portable mode detection (before any app imports) ─────────────────────────
_portable = '--portable' in sys.argv or os.environ.get('ORBIT_PORTABLE', '') == '1'
if _portable:
    _script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    _data_dir = os.path.join(_script_dir, 'orbit-data')
    os.makedirs(_data_dir, exist_ok=True)
    # Patch storage module paths before they are used
    import app.storage as _storage_mod
    _storage_mod.STORAGE_DIR = _data_dir
    _storage_mod.STORAGE_FILE = os.path.join(_data_dir, 'workspace.json')
    _storage_mod.PROFILES_DIR = os.path.join(_data_dir, 'profiles')
    _storage_mod._WORKSPACES_FILE = os.path.join(_data_dir, 'workspaces.json')
    _storage_mod._SETTINGS_FILE = os.path.join(_data_dir, 'settings.json')
    import app.audit_log as _audit_mod
    _audit_mod.set_log_path(os.path.join(_data_dir, 'audit.log'))
    os.makedirs(_storage_mod.PROFILES_DIR, exist_ok=True)

# ── Single-instance guard (per Windows user) ──────────────────────────────────

def _ipc_name() -> str:
    """Socket name unique per Windows user — allows concurrent multi-user sessions."""
    import getpass
    user = getpass.getuser().replace(' ', '_').replace('\\', '_')
    return f'orbit-{user}'


def _try_single_instance():
    """Ensure only one Orbit per user. Returns QLocalServer if first instance, else None."""
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    name = _ipc_name()
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):
        sock.write(b'show\n')
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return None  # Another instance is running
    # We are the first instance — start listening
    QLocalServer.removeServer(name)  # Remove stale socket from previous crash
    server = QLocalServer()
    server.listen(name)
    return server


def _connect_ipc_server(server, win_holder: list) -> None:
    """Route incoming IPC connections to restore/raise the main window."""
    def _on_connection():
        conn = server.nextPendingConnection()
        conn.readyRead.connect(lambda: _on_data(conn))

    def _on_data(conn):
        data = bytes(conn.readAll()).strip()
        if data == b'show' and win_holder:
            w = win_holder[0]
            w.showNormal()
            w.raise_()
            w.activateWindow()
        conn.disconnectFromServer()

    server.newConnection.connect(_on_connection)


# # Chromium flags — must be set before QApplication is created# --disable-blink-features=AutomationControlled removes navigator.webdriver
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


class _AnimatedSplash:
    """Elegant splash with fade-in, pulsing title, and fade-out."""

    _MESSAGES = [
        'Iniciando Orbit...',
        'Carregando servicos...',
        'Configurando interface...',
        'Preparando workspace...',
        'Quase la...',
    ]

    def __init__(self, app: QApplication):
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
        from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QByteArray
        from PySide6.QtGui import QColor

        self._app = app
        W, H = 420, 280

        win = QWidget(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        win.setAttribute(Qt.WA_TranslucentBackground)
        win.setFixedSize(W, H)

        # Inner container with rounded corners
        inner = QWidget(win)
        inner.setFixedSize(W, H)
        inner.setObjectName('splashInner')
        inner.setStyleSheet(
            '#splashInner { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,'
            'stop:0 #12121a, stop:1 #1a1a28);'
            'border-radius: 16px; border: 1px solid rgba(124,106,247,0.15); }'
            '#splashInner QLabel { border: none; background: transparent; }'
        )
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 48, 0, 40)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # Stylized 'Orbit' title
        title = QLabel('Orbit')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            'color: #7c6af7; font-size: 42px; font-weight: 800;'
            ' font-family: Inter, Segoe UI, sans-serif;'
            ' letter-spacing: 6px; background: transparent;'
        )
        layout.addWidget(title)
        layout.addSpacing(8)

        # Subtitle
        sub = QLabel('Multi-service desktop shell')
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet('color: #45475a; font-size: 11px; background: transparent; letter-spacing: 1px;')
        layout.addWidget(sub)
        layout.addSpacing(24)

        # Status message
        self._msg_label = QLabel(self._MESSAGES[0])
        self._msg_label.setAlignment(Qt.AlignCenter)
        self._msg_label.setStyleSheet(
            'color: #6c7086; font-size: 10px; background: transparent;'
        )
        layout.addWidget(self._msg_label)

        # Loading dots animation
        self._dots = QLabel('')
        self._dots.setAlignment(Qt.AlignCenter)
        self._dots.setStyleSheet('color: #7c6af7; font-size: 18px; background: transparent; letter-spacing: 4px;')
        self._dots.setFixedHeight(20)
        layout.addWidget(self._dots)
        self._dot_count = 0

        # Center on screen
        screen = app.primaryScreen().geometry()
        win.move((screen.width() - W) // 2, (screen.height() - H) // 2)

        # Fade-in effect
        self._opacity = QGraphicsOpacityEffect(win)
        self._opacity.setOpacity(0.0)
        win.setGraphicsEffect(self._opacity)
        self._fade_in = QPropertyAnimation(self._opacity, QByteArray(b'opacity'), win)
        self._fade_in.setDuration(600)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        win.show()
        self._fade_in.start()
        self._win = win
        self._msg_idx = 0

        # Message cycling timer
        self._msg_timer = QTimer()
        self._msg_timer.setInterval(900)
        self._msg_timer.timeout.connect(self._next_message)
        self._msg_timer.start()

        # Dots animation timer
        self._dot_timer = QTimer()
        self._dot_timer.setInterval(300)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start()

        app.processEvents()

    def _next_message(self) -> None:
        self._msg_idx = (self._msg_idx + 1) % len(self._MESSAGES)
        self._msg_label.setText(self._MESSAGES[self._msg_idx])
        self._app.processEvents()

    def _animate_dots(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        self._dots.setText('.' * self._dot_count if self._dot_count else '')
        self._app.processEvents()

    def set_message(self, text: str) -> None:
        self._msg_label.setText(text)
        self._app.processEvents()

    def finish(self, win) -> None:
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QByteArray, QTimer
        self._msg_timer.stop()
        self._dot_timer.stop()
        # Fade-out
        self._fade_out = QPropertyAnimation(self._opacity, QByteArray(b'opacity'), self._win)
        self._fade_out.setDuration(400)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self._win.close)
        self._fade_out.start()
        # Process events during fade
        QTimer.singleShot(450, lambda: None)


def _show_splash(app: QApplication) -> '_AnimatedSplash':
    return _AnimatedSplash(app)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Orbit')
    app.setOrganizationName('Orbit')
    app.setQuitOnLastWindowClosed(False)

    # Single-instance guard — one Orbit per Windows user, multiple users can run in parallel
    _ipc_server = _try_single_instance()
    if _ipc_server is None:
        # Another instance of Orbit is already running for this user
        sys.exit(0)

    _load_fonts()

    font = QFont('Inter', 10)
    app.setFont(font)

    splash = _show_splash(app)

    # Hook so OrbitWindow.__init__ can pump events, keeping animation alive
    import app.window as _wmod
    _wmod._splash_tick = lambda: app.processEvents()

    from PySide6.QtCore import QTimer as _QT

    win_holder: list = []

    messages = [
        ('Alinhando planetas...',        300),
        ('Carregando serviços...',        600),
        ('Calibrando órbitas...',         600),
        ('Sincronizando galáxias...',     700),
        ('Estabelecendo conexões...',     700),
        ('Carregando bibliotecas...',     700),
        ('Inicializando protocolos...',   700),
        ('Finalizando realinhamento...', 700),
        ('Quase pronto...',               400),
    ]
    _chain: list = []

    def _create_window():
        splash.set_message('Iniciando interface...')
        win = OrbitWindow()
        _wmod._splash_tick = None
        if _portable:
            from app.i18n import t
            win.setWindowTitle(f'Orbit [{t("portable_mode")}]')
        win_holder.append(win)
        _connect_ipc_server(_ipc_server, win_holder)  # Route "show" from 2nd-instance attempts
        win.show()
        splash.finish(win)
        url = _parse_url_scheme(sys.argv[1:])
        if url:
            win.handle_url_scheme(url)

    def _make_stage(remaining):
        if not remaining:
            _create_window()
            return
        msg, delay = remaining[0]
        splash.set_message(msg)
        _QT.singleShot(delay, lambda: _make_stage(remaining[1:]))

    _QT.singleShot(0, lambda: _make_stage(messages))
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

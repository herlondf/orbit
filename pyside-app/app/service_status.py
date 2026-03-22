"""service_status.py — Per-service network status checker."""
from __future__ import annotations
import time
from PySide6.QtCore import QObject, Signal, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class ServiceStatusChecker(QObject):
    status_changed = Signal(str, str)  # service_id, status: 'online'|'slow'|'offline'

    def __init__(self, services: list, parent=None):
        # services: list of (service_id, url) tuples
        super().__init__(parent)
        self._services = list(services)
        self._nam = QNetworkAccessManager(self)
        self._pending: dict = {}  # reply -> (service_id, start_time)
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self._check_all)

    def start(self):
        self._check_all()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def set_services(self, services: list):
        self._services = list(services)

    def _check_all(self):
        for svc_id, url in self._services:
            self._check_one(svc_id, url)

    def _check_one(self, svc_id: str, url: str):
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                         QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = self._nam.head(req)
        start = time.monotonic()
        self._pending[reply] = (svc_id, start)
        reply.finished.connect(lambda r=reply: self._on_reply(r))

    def _on_reply(self, reply: QNetworkReply):
        info = self._pending.pop(reply, None)
        if not info:
            reply.deleteLater()
            return
        svc_id, start = info
        elapsed = time.monotonic() - start
        error = reply.error()
        reply.deleteLater()
        if error != QNetworkReply.NetworkError.NoError:
            status = 'offline'
        elif elapsed < 2.0:
            status = 'online'
        elif elapsed < 5.0:
            status = 'slow'
        else:
            status = 'offline'
        self.status_changed.emit(svc_id, status)

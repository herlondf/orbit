"""security_monitor.py — Lightweight security monitor with keylogger heuristics."""
from __future__ import annotations
import sys
from PySide6.QtCore import QObject, Signal, QTimer

_SUSPICIOUS_NAMES = frozenset({
    'keylogger', 'keysniffer', 'spy', 'spyware', 'ratclient', 'backdoor',
    'metasploit', 'meterpreter', 'cobaltstrike', 'beacon', 'mimikatz',
    'ncat', 'netcat', 'wireshark', 'fiddler', 'charles', 'procmon',
    'processhacker', 'ollydbg', 'x64dbg', 'x32dbg', 'cheatengine',
    'hook', 'inject', 'payload', 'shell32hook', 'winspy', 'revealer',
    'actual keylogger', 'perfect keylogger', 'ardamax', 'refog',
})


class SecurityMonitor(QObject):
    """Monitor for potential security threats (keyloggers, malware)."""

    threat_detected = Signal(str)  # description of threat

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)  # check every 30s
        self._timer.timeout.connect(self._check)
        self._known_pids: set = set()

    def start(self):
        self._check()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _check(self):  # pragma: no cover
        if sys.platform != 'win32':
            return
        try:
            self._check_processes()
        except Exception:
            pass

    def _check_processes(self):  # pragma: no cover
        try:
            import ctypes
            import ctypes.wintypes

            TH32CS_SNAPPROCESS = 0x00000002

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ('dwSize', ctypes.wintypes.DWORD),
                    ('cntUsage', ctypes.wintypes.DWORD),
                    ('th32ProcessID', ctypes.wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
                    ('th32ModuleID', ctypes.wintypes.DWORD),
                    ('cntThreads', ctypes.wintypes.DWORD),
                    ('th32ParentProcessID', ctypes.wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long),
                    ('dwFlags', ctypes.wintypes.DWORD),
                    ('szExeFile', ctypes.c_char * 260),
                ]

            snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            entry = PROCESSENTRY32()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

            if ctypes.windll.kernel32.Process32First(snap, ctypes.byref(entry)):
                while True:
                    name = entry.szExeFile.decode('utf-8', errors='ignore').lower()
                    pid = entry.th32ProcessID
                    name_base = name.replace('.exe', '').replace('.dll', '').replace('-', '').replace('_', '')
                    for suspicious in _SUSPICIOUS_NAMES:
                        clean = suspicious.replace(' ', '').replace('-', '')
                        if clean in name_base and pid not in self._known_pids:
                            self._known_pids.add(pid)
                            self.threat_detected.emit(
                                f'Processo suspeito detectado: {name} (PID {pid})'
                            )
                    if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(entry)):
                        break

            ctypes.windll.kernel32.CloseHandle(snap)
        except Exception:
            pass

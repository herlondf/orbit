"""sounds.py — Notification sound playback for Orbit."""
from __future__ import annotations

import os
from typing import List, Any

# Keep references alive until playback completes
_active: List[Any] = []


def play_sound(path: str) -> None:
    """Play a notification sound file (.wav via QSoundEffect, others via QMediaPlayer)."""
    if not path or not os.path.isfile(path):
        return
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == '.wav':
            from PySide6.QtMultimedia import QSoundEffect
            from PySide6.QtCore import QUrl
            sfx = QSoundEffect()
            sfx.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            sfx.setVolume(1.0)
            sfx.play()
            _active.append(sfx)
            # Clean up finished sounds to avoid accumulation
            _cleanup()
        else:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PySide6.QtCore import QUrl
            player = QMediaPlayer()
            audio = QAudioOutput()
            player.setAudioOutput(audio)
            audio.setVolume(1.0)
            player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            player.play()
            _active.append((player, audio))
            _cleanup()
    except Exception as e:
        print(f'[sounds] Error playing {path}: {e}')


def _cleanup() -> None:
    """Remove finished QSoundEffect instances."""
    to_remove = []
    for item in _active:
        if isinstance(item, tuple):
            continue  # keep QMediaPlayer pairs
        try:
            from PySide6.QtMultimedia import QSoundEffect
            if isinstance(item, QSoundEffect) and not item.isPlaying():
                to_remove.append(item)
        except Exception:
            pass
    for item in to_remove:
        _active.remove(item)

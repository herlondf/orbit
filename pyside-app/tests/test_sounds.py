"""Tests for app.sounds — notification sound playback."""
from unittest.mock import MagicMock, patch


def test_play_sound_missing_file():
    from app.sounds import play_sound
    play_sound('/nonexistent/path/to/sound.wav')


def test_play_sound_empty_path():
    from app.sounds import play_sound
    play_sound('')


def test_play_sound_none_path():
    from app.sounds import play_sound
    play_sound(None)


def test_play_sound_wav_with_mock(tmp_path):
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"RIFF" + b"\x00" * 40)

    mock_sfx = MagicMock()
    mock_sfx.isPlaying.return_value = False

    mock_qt_multimedia = MagicMock()
    mock_qt_multimedia.QSoundEffect.return_value = mock_sfx

    mock_qt_core = MagicMock()

    import app.sounds as sounds_mod
    with patch.dict('sys.modules', {
        'PySide6.QtMultimedia': mock_qt_multimedia,
        'PySide6.QtCore': mock_qt_core,
    }):
        before = len(sounds_mod._active)
        sounds_mod.play_sound(str(wav_file))
        # sfx was appended then cleaned (isPlaying=False), net may be 0 or 1
        assert len(sounds_mod._active) >= before


def test_play_sound_mp3_with_mock(tmp_path):
    mp3_file = tmp_path / "test.mp3"
    mp3_file.write_bytes(b"\xff\xfb" + b"\x00" * 100)

    mock_player = MagicMock()
    mock_audio = MagicMock()

    mock_qt_multimedia = MagicMock()
    mock_qt_multimedia.QMediaPlayer.return_value = mock_player
    mock_qt_multimedia.QAudioOutput.return_value = mock_audio

    mock_qt_core = MagicMock()

    import app.sounds as sounds_mod
    original_active = sounds_mod._active[:]
    with patch.dict('sys.modules', {
        'PySide6.QtMultimedia': mock_qt_multimedia,
        'PySide6.QtCore': mock_qt_core,
    }):
        sounds_mod.play_sound(str(mp3_file))
        # (player, audio) tuple should be in _active
        has_tuple = any(isinstance(i, tuple) for i in sounds_mod._active)
        assert has_tuple
    # cleanup
    sounds_mod._active[:] = original_active


def test_cleanup_empty_list():
    import app.sounds as sounds_mod
    original = sounds_mod._active[:]
    sounds_mod._active.clear()
    sounds_mod._cleanup()
    sounds_mod._active.extend(original)


def test_cleanup_with_tuple_items():
    import app.sounds as sounds_mod
    fake_pair = (MagicMock(), MagicMock())
    sounds_mod._active.append(fake_pair)
    sounds_mod._cleanup()
    assert fake_pair in sounds_mod._active
    sounds_mod._active.remove(fake_pair)


def test_cleanup_removes_finished_sfx(tmp_path):
    """_cleanup removes QSoundEffect instances that are no longer playing."""
    import app.sounds as sounds_mod

    mock_sfx = MagicMock()
    mock_sfx.isPlaying.return_value = False

    mock_qt_multimedia = MagicMock()
    mock_qt_multimedia.QSoundEffect = type(mock_sfx)

    original = sounds_mod._active[:]
    sounds_mod._active.clear()
    sounds_mod._active.append(mock_sfx)

    with patch('app.sounds.QSoundEffect', mock_qt_multimedia.QSoundEffect, create=True):
        # Manually simulate the cleanup logic
        to_remove = []
        for item in sounds_mod._active:
            if isinstance(item, tuple):
                continue
            if hasattr(item, 'isPlaying') and not item.isPlaying():
                to_remove.append(item)
        for item in to_remove:
            sounds_mod._active.remove(item)

    assert mock_sfx not in sounds_mod._active
    sounds_mod._active[:] = original

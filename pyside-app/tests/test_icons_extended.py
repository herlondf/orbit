"""Tests for app.icons — SVG icon system."""
import pytest
from unittest.mock import MagicMock, patch


def test_icon_cache_path_returns_path():
    from app.icons import icon_cache_path
    from pathlib import Path
    p = icon_cache_path('https://example.com/icon.png')
    assert isinstance(p, Path)
    assert p.suffix == '.png'


def test_icon_cache_path_deterministic():
    from app.icons import icon_cache_path
    p1 = icon_cache_path('https://example.com/icon.png')
    p2 = icon_cache_path('https://example.com/icon.png')
    assert p1 == p2


def test_icon_cache_path_different_urls():
    from app.icons import icon_cache_path
    p1 = icon_cache_path('https://a.com/icon.png')
    p2 = icon_cache_path('https://b.com/icon.png')
    assert p1 != p2


def test_get_cached_pixmap_missing_file(tmp_path, monkeypatch):
    from app.icons import get_cached_pixmap, ICONS_DIR
    import app.icons as icons_mod
    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)
    result = get_cached_pixmap('https://example.com/nonexistent.png')
    assert result is None


def test_icon_returns_qicon(qtbot):
    from app.icons import icon
    from PySide6.QtGui import QIcon
    ic = icon('plus', size=16)
    assert isinstance(ic, QIcon)
    assert not ic.isNull()


def test_icon_unknown_name_falls_back(qtbot):
    from app.icons import icon
    from PySide6.QtGui import QIcon
    # Unknown name should fall back to information-circle
    ic = icon('nonexistent_icon_name', size=16)
    assert isinstance(ic, QIcon)
    assert not ic.isNull()


def test_icon_different_sizes(qtbot):
    from app.icons import icon
    for size in (12, 16, 24, 32):
        ic = icon('plus', size=size)
        assert not ic.isNull()


def test_icon_different_colors(qtbot):
    from app.icons import icon
    ic1 = icon('bell', color='#ff0000')
    ic2 = icon('bell', color='#00ff00')
    assert not ic1.isNull()
    assert not ic2.isNull()


def test_icon_known_names(qtbot):
    from app.icons import icon
    for name in ('trash', 'pencil', 'cog-6-tooth', 'bell', 'lock-closed', 'folder'):
        ic = icon(name)
        assert not ic.isNull(), f"Icon '{name}' is null"


def test_icon_label_returns_label(qtbot):
    from app.icons import icon_label
    from PySide6.QtWidgets import QLabel
    lbl = icon_label('plus', size=16)
    assert isinstance(lbl, QLabel)
    qtbot.addWidget(lbl)


def test_icon_label_has_correct_size(qtbot):
    from app.icons import icon_label
    lbl = icon_label('bell', size=24)
    qtbot.addWidget(lbl)
    assert lbl.width() == 24
    assert lbl.height() == 24


def test_make_svg_returns_bytes():
    from app.icons import _make_svg
    result = _make_svg('<path d="M0 0"/>', '#ffffff', 16)
    assert isinstance(result, bytes)
    assert b'<svg' in result
    assert b'16' in result


def test_get_cached_pixmap_existing_file(qtbot, tmp_path, monkeypatch):
    """get_cached_pixmap returns pixmap when valid file exists."""
    from app.icons import get_cached_pixmap
    import app.icons as icons_mod
    import hashlib
    from pathlib import Path
    from PySide6.QtGui import QPixmap

    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)

    url = 'https://example.com/valid.png'
    h = hashlib.md5(url.encode()).hexdigest()
    cache_path = tmp_path / f'{h}.png'
    # Create a real small pixmap and save it
    px = QPixmap(2, 2)
    px.save(str(cache_path))

    result = get_cached_pixmap(url)
    assert result is not None
    assert not result.isNull()


def test_get_cached_pixmap_null_pixmap(qtbot, tmp_path, monkeypatch):
    """get_cached_pixmap returns None when file is corrupted/null."""
    from app.icons import get_cached_pixmap
    import app.icons as icons_mod
    import hashlib

    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)

    url = 'https://example.com/corrupt.png'
    h = hashlib.md5(url.encode()).hexdigest()
    cache_path = tmp_path / f'{h}.png'
    # Write invalid image data
    cache_path.write_bytes(b'NOT A PNG')

    result = get_cached_pixmap(url)
    assert result is None


def test_icon_fetcher_fetch_uncached_makes_request(qtbot, tmp_path, monkeypatch):
    """fetch() for uncached URL makes a network request."""
    from app.icons import IconFetcher
    import app.icons as icons_mod
    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)

    fetcher = IconFetcher()
    from unittest.mock import MagicMock, patch
    with patch.object(fetcher._mgr, 'get', return_value=MagicMock()) as mock_get:
        fetcher.fetch('https://example.com/uncached.png')
    mock_get.assert_called_once()


def test_icon_fetcher_on_finished_no_url(qtbot, tmp_path, monkeypatch):
    """_on_finished with no URL in pending dict calls deleteLater."""
    from app.icons import IconFetcher
    import app.icons as icons_mod
    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)

    fetcher = IconFetcher()
    mock_reply = MagicMock()
    mock_reply.error.return_value = None  # won't be called since url is None
    # pop returns None since reply not in pending
    fetcher._pending = {}

    fetcher._on_finished(mock_reply)
    mock_reply.deleteLater.assert_called_once()


def test_icon_fetcher_on_finished_with_error(qtbot, tmp_path, monkeypatch):
    """_on_finished with network error still calls deleteLater."""
    from app.icons import IconFetcher
    import app.icons as icons_mod
    from PySide6.QtNetwork import QNetworkReply
    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)

    fetcher = IconFetcher()
    mock_reply = MagicMock()
    mock_reply.error.return_value = QNetworkReply.NetworkError.ConnectionRefusedError
    fetcher._pending[mock_reply] = 'https://example.com/test.png'

    fetcher._on_finished(mock_reply)
    mock_reply.deleteLater.assert_called_once()



def test_icon_fetcher_fetch_cached(qtbot, tmp_path, monkeypatch):
    """Test fetch() when the icon is already cached."""
    from app.icons import IconFetcher
    import app.icons as icons_mod
    from pathlib import Path
    from PySide6.QtGui import QPixmap

    # Create a valid cached icon
    monkeypatch.setattr(icons_mod, 'ICONS_DIR', tmp_path)

    fetcher = IconFetcher()
    received = []
    fetcher.fetched.connect(lambda url, px: received.append((url, px)))

    # Create a real 1x1 pixel PNG as fake cache
    px = QPixmap(1, 1)
    import hashlib
    url = 'https://example.com/test.png'
    h = hashlib.md5(url.encode()).hexdigest()
    cache_path = tmp_path / f'{h}.png'
    px.save(str(cache_path))

    fetcher.fetch(url)
    # Signal should have been emitted synchronously for cached
    assert len(received) == 1
    assert received[0][0] == url

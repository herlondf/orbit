"""Tests for app.brand_icons — brand SVG icons."""


def test_brand_data_exists():
    from app.brand_icons import _BRAND_DATA
    assert isinstance(_BRAND_DATA, dict)
    assert len(_BRAND_DATA) > 10


def test_brand_data_keys_are_strings():
    from app.brand_icons import _BRAND_DATA
    for key in _BRAND_DATA:
        assert isinstance(key, str)


def test_brand_data_values_are_tuples():
    from app.brand_icons import _BRAND_DATA
    for key, val in _BRAND_DATA.items():
        assert isinstance(val, tuple) and len(val) == 2


def test_has_brand_icon_known():
    from app.brand_icons import has_brand_icon
    assert has_brand_icon('whatsapp') is True
    assert has_brand_icon('slack') is True
    assert has_brand_icon('github') is True


def test_has_brand_icon_unknown():
    from app.brand_icons import has_brand_icon
    assert has_brand_icon('nonexistent_service') is False


def test_brand_icon_returns_pixmap(qtbot):
    from app.brand_icons import brand_icon
    from PySide6.QtGui import QPixmap
    px = brand_icon('whatsapp', 24)
    assert isinstance(px, QPixmap)
    assert not px.isNull()


def test_brand_icon_unknown_returns_empty(qtbot):
    from app.brand_icons import brand_icon
    from PySide6.QtGui import QPixmap
    px = brand_icon('nonexistent_xyz', 24)
    assert isinstance(px, QPixmap)
    assert px.isNull()


def test_brand_icon_slack(qtbot):
    from app.brand_icons import brand_icon
    px = brand_icon('slack', 32)
    assert not px.isNull()


def test_brand_icon_multiple_services(qtbot):
    from app.brand_icons import brand_icon
    for stype in ('telegram', 'discord', 'github', 'gmail', 'youtube'):
        px = brand_icon(stype, 16)
        assert not px.isNull(), f"Expected pixmap for {stype}"


def test_brand_data_has_hex_colors():
    from app.brand_icons import _BRAND_DATA
    for name, (path_d, color) in _BRAND_DATA.items():
        assert color.startswith('#'), f"{name} color not hex: {color}"
        assert isinstance(path_d, str) and len(path_d) > 10, f"{name} has empty path"

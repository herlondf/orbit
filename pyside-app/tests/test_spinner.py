"""Tests for app.spinner — rotating arc spinner widget."""
from PySide6.QtGui import QColor


def test_spinner_instantiation(qtbot):
    from app.spinner import Spinner
    sp = Spinner()
    qtbot.addWidget(sp)
    assert sp is not None


def test_spinner_custom_size(qtbot):
    from app.spinner import Spinner
    sp = Spinner(size=40, color='#ff0000', stroke=5)
    qtbot.addWidget(sp)
    assert sp.width() == 40
    assert sp.height() == 40


def test_spinner_stop_start(qtbot):
    from app.spinner import Spinner
    sp = Spinner()
    qtbot.addWidget(sp)
    sp.stop()
    sp.start()


def test_spinner_set_color(qtbot):
    from app.spinner import Spinner
    sp = Spinner()
    qtbot.addWidget(sp)
    sp.set_color('#123456')
    assert sp._color == QColor('#123456')


def test_spinner_rotate(qtbot):
    from app.spinner import Spinner
    sp = Spinner()
    qtbot.addWidget(sp)
    sp._angle = 0
    sp._rotate()
    assert sp._angle == 6

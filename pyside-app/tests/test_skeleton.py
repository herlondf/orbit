"""Tests for app.skeleton — skeleton loader widget."""


def test_skeleton_widget_instantiation(qtbot):
    from app.skeleton import SkeletonWidget
    w = SkeletonWidget(lines=3)
    qtbot.addWidget(w)
    assert w is not None


def test_skeleton_widget_default_lines(qtbot):
    from app.skeleton import SkeletonWidget
    w = SkeletonWidget()
    qtbot.addWidget(w)
    assert w is not None


def test_skeleton_bar_instantiation(qtbot):
    from app.skeleton import _SkeletonBar
    bar = _SkeletonBar(width_pct=0.8, height=14)
    qtbot.addWidget(bar)
    assert bar is not None


def test_skeleton_widget_stop(qtbot):
    from app.skeleton import SkeletonWidget
    w = SkeletonWidget(lines=2)
    qtbot.addWidget(w)
    w.stop()


def test_skeleton_bar_width_pct(qtbot):
    from app.skeleton import _SkeletonBar
    bar = _SkeletonBar(width_pct=0.5, height=10)
    qtbot.addWidget(bar)
    assert bar._width_pct == 0.5

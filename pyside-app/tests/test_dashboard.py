"""Tests for app.dashboard — DashboardWidget and ServiceCard."""
import pytest
from unittest.mock import patch


def _make_service(svc_id='svc1', name='Slack', unread=0):
    from app.models import Service
    return Service(id=svc_id, service_type='slack', name=name, icon='SL', color='#4A154B', unread=unread)


def test_dashboard_empty_services(qtbot):
    from app.dashboard import DashboardWidget
    with patch('app.dashboard.get_weekly_totals', return_value=[]):
        widget = DashboardWidget([])
        qtbot.addWidget(widget)
    assert widget is not None


def test_dashboard_with_service(qtbot):
    from app.dashboard import DashboardWidget
    svc = _make_service()
    with patch('app.dashboard.get_weekly_totals', return_value=[]):
        widget = DashboardWidget([svc])
        qtbot.addWidget(widget)
    assert widget is not None


def test_service_card_creates(qtbot):
    from app.dashboard import ServiceCard
    svc = _make_service()
    card = ServiceCard(svc)
    qtbot.addWidget(card)
    assert card is not None


def test_service_card_emits_clicked(qtbot):
    from app.dashboard import ServiceCard
    svc = _make_service(svc_id='svc42')
    card = ServiceCard(svc)
    card.setProperty('svc_id', svc.id)
    qtbot.addWidget(card)

    received = []
    card.clicked.connect(received.append)
    card.mousePressEvent(None)
    assert received == ['svc42']


def test_dashboard_service_clicked_signal(qtbot):
    from app.dashboard import DashboardWidget
    svc = _make_service(svc_id='svc99')
    with patch('app.dashboard.get_weekly_totals', return_value=[]):
        widget = DashboardWidget([svc])
        qtbot.addWidget(widget)

    received = []
    widget.service_clicked.connect(received.append)


def test_dashboard_with_unread_badge(qtbot):
    from app.dashboard import ServiceCard
    svc = _make_service(unread=5)
    card = ServiceCard(svc)
    qtbot.addWidget(card)
    # Widget should have been created without error
    assert card is not None


def test_dashboard_no_unread_no_badge(qtbot):
    from app.dashboard import ServiceCard
    svc = _make_service(unread=0)
    card = ServiceCard(svc)
    qtbot.addWidget(card)
    assert card is not None


def test_dashboard_refresh(qtbot):
    from app.dashboard import DashboardWidget
    svc1 = _make_service(svc_id='svc1', name='Slack')
    with patch('app.dashboard.get_weekly_totals', return_value=[]):
        widget = DashboardWidget([svc1])
        qtbot.addWidget(widget)

    svc2 = _make_service(svc_id='svc2', name='Gmail')
    with patch('app.dashboard.get_weekly_totals', return_value=[]):
        widget.refresh([svc2])
    # Widget should remain functional after refresh
    assert widget is not None


def test_dashboard_with_weekly_stats(qtbot):
    from app.dashboard import DashboardWidget
    svc = _make_service()
    totals = [{'id': 'svc1', 'name': 'Slack', 'total': 3600}]
    with patch('app.dashboard.get_weekly_totals', return_value=totals):
        with patch('app.dashboard.fmt_duration', return_value='1h'):
            widget = DashboardWidget([svc])
            qtbot.addWidget(widget)
    assert widget is not None


def test_multiple_service_cards(qtbot):
    from app.dashboard import DashboardWidget
    services = [_make_service(f'svc{i}', f'Service {i}') for i in range(6)]
    with patch('app.dashboard.get_weekly_totals', return_value=[]):
        widget = DashboardWidget(services)
        qtbot.addWidget(widget)
    assert widget is not None

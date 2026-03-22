"""Tests for app.models dataclasses."""
import pytest


def test_account_defaults():
    from app.models import Account
    acc = Account(id='a1', label='Me', url='https://x.com', profile_name='p1')
    assert acc.notifications == 'native'
    assert acc.authuser == 0


def test_account_fields():
    from app.models import Account
    acc = Account(id='a1', label='Work', url='https://slack.com', profile_name='p2',
                  notifications='muted', authuser=2)
    assert acc.id == 'a1'
    assert acc.label == 'Work'
    assert acc.url == 'https://slack.com'
    assert acc.profile_name == 'p2'
    assert acc.notifications == 'muted'
    assert acc.authuser == 2


def test_service_defaults():
    from app.models import Service
    svc = Service(id='s1', service_type='slack', name='Slack', icon='SL', color='#fff')
    assert svc.accounts == []
    assert svc.unread == 0
    assert svc.hibernate_after is None
    assert svc.pinned is False
    assert svc.custom_css == ''
    assert svc.custom_js == ''
    assert svc.zoom == 1.0
    assert svc.notification_sound == ''
    assert svc.incognito is False
    assert svc.proxy == ''


def test_service_fields_mutable():
    from app.models import Service
    svc = Service(id='s1', service_type='slack', name='Slack', icon='SL', color='#fff')
    svc.accounts.append('x')
    assert len(svc.accounts) == 1


def test_service_all_fields():
    from app.models import Service, Account
    acc = Account(id='a1', label='L', url='u', profile_name='p')
    svc = Service(
        id='s2', service_type='gmail', name='Gmail', icon='GM', color='#red',
        accounts=[acc], unread=5, hibernate_after=30, pinned=True,
        custom_css='body{}', custom_js='alert(1)', zoom=1.5,
        notification_sound='ding', incognito=True, proxy='http://proxy:8080',
    )
    assert svc.unread == 5
    assert svc.hibernate_after == 30
    assert svc.pinned is True
    assert svc.custom_css == 'body{}'
    assert svc.custom_js == 'alert(1)'
    assert svc.zoom == 1.5
    assert svc.notification_sound == 'ding'
    assert svc.incognito is True
    assert svc.proxy == 'http://proxy:8080'
    assert svc.accounts[0].id == 'a1'


def test_service_group_defaults():
    from app.models import ServiceGroup
    g = ServiceGroup(id='g1', name='Group', service_ids=['s1', 's2'])
    assert g.collapsed is False
    assert g.service_ids == ['s1', 's2']


def test_service_group_collapsed():
    from app.models import ServiceGroup
    g = ServiceGroup(id='g1', name='Group', service_ids=[], collapsed=True)
    assert g.collapsed is True


def test_workspace_defaults():
    from app.models import Workspace
    ws = Workspace(id='ws1', name='Main')
    assert ws.services == []
    assert ws.groups == []


def test_workspace_with_services(sample_service):
    from app.models import Workspace
    ws = Workspace(id='ws1', name='Main', services=[sample_service])
    assert len(ws.services) == 1
    assert ws.services[0].id == 'svc1'


def test_workspace_groups():
    from app.models import Workspace, ServiceGroup
    g = ServiceGroup(id='g1', name='Dev', service_ids=['s1'])
    ws = Workspace(id='ws1', name='Main', groups=[g])
    assert len(ws.groups) == 1
    assert ws.groups[0].name == 'Dev'


def test_new_id_format():
    from app.models import new_id
    uid = new_id()
    assert len(uid) == 8

    uid_prefix = new_id('svc')
    assert uid_prefix.startswith('svc-')
    assert len(uid_prefix) == 12


def test_slugify():
    from app.models import slugify
    assert slugify('Hello World!') == 'hello-world'
    assert slugify('  Test  ') == 'test'
    assert slugify('foo-bar') == 'foo-bar'
    assert slugify('Café & Tea') == 'caf-tea'

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from .models import Account, Service, Workspace

# Map Rambox/Ferdium service types to Orbit catalog types
SERVICE_MAP = {
    # Rambox names
    'WhatsApp': 'whatsapp',
    'Slack': 'slack',
    'Gmail': 'gmail',
    'Telegram': 'telegram',
    'Discord': 'discord',
    'Microsoft Teams': 'teams',
    'Google Chat': 'googlechat',
    'Google Meet': 'googlemeet',
    'Notion': 'notion',
    'Linear': 'linear',
    'Zoom': 'zoom',
    'Twitch': 'twitch',
    'YouTube': 'youtube',
    'Reddit': 'reddit',
    'Twitter': 'twitter',
    'Facebook Messenger': 'messenger',
    # Ferdium names (often same but lowercase)
    'whatsapp': 'whatsapp',
    'slack': 'slack',
    'gmail': 'gmail',
    'telegram': 'telegram',
    'discord': 'discord',
    'msteams': 'teams',
    'googleChat': 'googlechat',
}

ICON_MAP = {
    'whatsapp': '💬', 'slack': '💼', 'gmail': '📧', 'telegram': '✈️',
    'discord': '🎮', 'teams': '👥', 'googlechat': '💬', 'googlemeet': '🎥',
    'notion': '📝', 'linear': '📐', 'zoom': '📹', 'twitch': '🎮',
    'youtube': '▶️', 'reddit': '🤖', 'twitter': '🐦', 'messenger': '💬',
}

COLOR_MAP = {
    'whatsapp': '#25D366', 'slack': '#4A154B', 'gmail': '#EA4335',
    'telegram': '#2CA5E0', 'discord': '#5865F2', 'teams': '#6264A7',
    'googlechat': '#1A73E8', 'googlemeet': '#00BCD4',
}


def import_rambox(filepath: str) -> Optional[Workspace]:
    """Parse Rambox config JSON and return a Workspace."""
    try:
        data = json.loads(Path(filepath).read_text(encoding='utf-8'))
        services_raw = []
        if isinstance(data, list):
            services_raw = data
        elif 'services' in data:
            services_raw = data['services']
        elif 'workspaces' in data:
            services_raw = data['workspaces'][0].get('services', [])

        services = []
        for svc_data in services_raw:
            name = svc_data.get('name', svc_data.get('label', 'Serviço'))
            stype_raw = svc_data.get('type', svc_data.get('service', ''))
            stype = SERVICE_MAP.get(stype_raw, 'custom')
            icon = ICON_MAP.get(stype, '🌐')
            color = COLOR_MAP.get(stype, '#7c4dff')
            url = svc_data.get('url', svc_data.get('customUrl', ''))

            account = Account(
                id=str(uuid.uuid4()),
                label=name,
                url=url,
                profile_name=str(uuid.uuid4()),
            )
            svc = Service(
                id=str(uuid.uuid4()),
                service_type=stype,
                name=name,
                icon=icon,
                color=color,
                accounts=[account],
            )
            services.append(svc)

        return Workspace(id=str(uuid.uuid4()), name='Importado', services=services)
    except Exception as e:
        raise ValueError(f'Erro ao importar: {e}')


def import_ferdium(filepath: str) -> Optional[Workspace]:
    """Parse Ferdium config (user-data/app.json or services JSON)."""
    try:
        data = json.loads(Path(filepath).read_text(encoding='utf-8'))
        services_raw = data.get('services', data if isinstance(data, list) else [])

        services = []
        for svc_data in services_raw:
            name = svc_data.get('name', 'Serviço')
            recipe = svc_data.get('recipe', {})
            if isinstance(recipe, dict):
                stype_raw = recipe.get('id', '')
            else:
                stype_raw = svc_data.get('type', '')
            stype = SERVICE_MAP.get(stype_raw, 'custom')
            icon = ICON_MAP.get(stype, '🌐')
            color = COLOR_MAP.get(stype, '#7c4dff')
            url = svc_data.get('url', svc_data.get('customUrl', ''))

            account = Account(
                id=str(uuid.uuid4()),
                label=name,
                url=url,
                profile_name=str(uuid.uuid4()),
            )
            svc = Service(
                id=str(uuid.uuid4()),
                service_type=stype,
                name=name,
                icon=icon,
                color=color,
                accounts=[account],
            )
            services.append(svc)

        return Workspace(id=str(uuid.uuid4()), name='Ferdium Import', services=services)
    except Exception as e:
        raise ValueError(f'Erro ao importar Ferdium: {e}')

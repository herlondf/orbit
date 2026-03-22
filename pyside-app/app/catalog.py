from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# Google service types that support the /u/{authuser}/ URL pattern
GOOGLE_TYPES = {'gmail', 'gchat', 'gcalendar', 'gmeet'}

# URL templates with {authuser} placeholder
_GOOGLE_URL_TEMPLATES = {
    'gmail':     'https://mail.google.com/mail/u/{authuser}/',
    'gchat':     'https://chat.google.com/u/{authuser}/',
    'gcalendar': 'https://calendar.google.com/calendar/u/{authuser}/r',
    'gmeet':     'https://meet.google.com/?authuser={authuser}',
}


def google_url(service_type: str, authuser: int) -> str:
    """Return the correct Google service URL for the given authuser index."""
    template = _GOOGLE_URL_TEMPLATES.get(service_type, '')
    return template.format(authuser=authuser) if template else ''


_FAVICON_BASE = 'https://www.google.com/s2/favicons?sz=64&domain='


@dataclass
class CatalogEntry:
    type: str
    name: str
    icon: str
    color: str
    default_url: str
    description: str
    favicon_url: str = ''
    category: str = ''


CATALOG: List[CatalogEntry] = [
    # ── Mensagens ──────────────────────────────────────────────────────────────
    CatalogEntry('whatsapp',    'WhatsApp',          'WA', '#2e936d', 'https://web.whatsapp.com/',               'Mensageiro pessoal e business',   _FAVICON_BASE + 'web.whatsapp.com',            'Mensagens'),
    CatalogEntry('telegram',    'Telegram',          'TG', '#2a8dc5', 'https://web.telegram.org/a/',             'Mensageiro com canais e bots',    _FAVICON_BASE + 'telegram.org',                'Mensagens'),
    CatalogEntry('signal',      'Signal',            'SG', '#3a76f0', 'https://signal.org/',                     'Mensageiro seguro',               _FAVICON_BASE + 'signal.org',                  'Mensagens'),
    CatalogEntry('messenger',   'Messenger',         'MS', '#0084ff', 'https://www.messenger.com/',              'Mensageiro Facebook',             _FAVICON_BASE + 'messenger.com',               'Mensagens'),
    CatalogEntry('line',        'Line',              'LI', '#00b900', 'https://line.me/',                        'Mensageiro popular na Ásia',      _FAVICON_BASE + 'line.me',                     'Mensagens'),
    CatalogEntry('viber',       'Viber',             'VB', '#7360f2', 'https://web.viber.com/',                  'Mensageiro e chamadas',           _FAVICON_BASE + 'viber.com',                   'Mensagens'),
    CatalogEntry('wechat',      'WeChat',            'WC', '#07c160', 'https://web.wechat.com/',                 'Mensageiro chinês',               _FAVICON_BASE + 'wechat.com',                  'Mensagens'),

    # ── Trabalho ───────────────────────────────────────────────────────────────
    CatalogEntry('slack',       'Slack',             'SL', '#d46d2a', 'https://app.slack.com/',                  'Mensageiro corporativo',          _FAVICON_BASE + 'slack.com',                   'Trabalho'),
    CatalogEntry('teams',       'Microsoft Teams',   'TM', '#6264a7', 'https://teams.microsoft.com/',            'Colaboração Microsoft',           _FAVICON_BASE + 'teams.microsoft.com',         'Trabalho'),
    CatalogEntry('discord',     'Discord',           'DC', '#456ae6', 'https://discord.com/app',                 'Comunidades e voz',               _FAVICON_BASE + 'discord.com',                 'Trabalho'),
    CatalogEntry('gchat',       'Google Chat',       'GC', '#1a73e8', 'https://chat.google.com/',                'Chat corporativo Google',         _FAVICON_BASE + 'chat.google.com',             'Trabalho'),
    CatalogEntry('zoom',        'Zoom',              'ZM', '#2d8cff', 'https://app.zoom.us/wc',                  'Videoconferência',                _FAVICON_BASE + 'zoom.us',                     'Trabalho'),
    CatalogEntry('webex',       'Webex',             'WX', '#00bceb', 'https://web.webex.com/',                  'Videoconferência Cisco',          _FAVICON_BASE + 'webex.com',                   'Trabalho'),
    CatalogEntry('skype',       'Skype',             'SK', '#00aff0', 'https://web.skype.com/',                  'Chamadas e mensagens Microsoft',  _FAVICON_BASE + 'skype.com',                   'Trabalho'),
    CatalogEntry('rocketchat',  'Rocket.Chat',       'RC', '#f5455c', 'https://rocket.chat/',                    'Chat open source',                _FAVICON_BASE + 'rocket.chat',                 'Trabalho'),
    CatalogEntry('mattermost',  'Mattermost',        'MM', '#0058cc', 'https://mattermost.com/',                 'Mensageiro open source',          _FAVICON_BASE + 'mattermost.com',              'Trabalho'),
    CatalogEntry('zulip',       'Zulip',             'ZP', '#6492fd', 'https://zulip.com/',                      'Chat com threading',              _FAVICON_BASE + 'zulip.com',                   'Trabalho'),

    # ── Email ──────────────────────────────────────────────────────────────────
    CatalogEntry('gmail',       'Gmail',             'GM', '#b95d4b', 'https://mail.google.com/',                'Email Google',                    _FAVICON_BASE + 'mail.google.com',             'Email'),
    CatalogEntry('outlook',     'Outlook',           'OL', '#0078d4', 'https://outlook.live.com/',               'Email Microsoft',                 _FAVICON_BASE + 'outlook.live.com',            'Email'),
    CatalogEntry('yahoomail',   'Yahoo Mail',        'YM', '#6001d2', 'https://mail.yahoo.com/',                 'Email Yahoo',                     _FAVICON_BASE + 'mail.yahoo.com',              'Email'),
    CatalogEntry('protonmail',  'ProtonMail',        'PM', '#6d4aff', 'https://mail.proton.me/',                 'Email criptografado',             _FAVICON_BASE + 'proton.me',                   'Email'),
    CatalogEntry('fastmail',    'Fastmail',          'FM', '#0068ff', 'https://app.fastmail.com/',               'Email rápido e privado',          _FAVICON_BASE + 'fastmail.com',                'Email'),
    CatalogEntry('tutanota',    'Tutanota',          'TT', '#840010', 'https://app.tuta.com/',                   'Email seguro e privado',          _FAVICON_BASE + 'tuta.com',                    'Email'),
    CatalogEntry('hey',         'Hey',               'HY', '#cc0000', 'https://app.hey.com/',                    'Email reimaginado',               _FAVICON_BASE + 'hey.com',                     'Email'),

    # ── Produtividade ──────────────────────────────────────────────────────────
    CatalogEntry('notion',      'Notion',            'NT', '#37352f', 'https://www.notion.so/',                  'Notas e documentação',            _FAVICON_BASE + 'notion.so',                   'Produtividade'),
    CatalogEntry('evernote',    'Evernote',          'EV', '#00a82d', 'https://www.evernote.com/',               'Notas e organização',             _FAVICON_BASE + 'evernote.com',                'Produtividade'),
    CatalogEntry('onenote',     'OneNote',           'ON', '#7719aa', 'https://www.onenote.com/',                'Notas Microsoft',                 _FAVICON_BASE + 'onenote.com',                 'Produtividade'),
    CatalogEntry('obsidian',    'Obsidian',          'OB', '#7c3aed', 'https://obsidian.md/',                    'Notas em Markdown',               _FAVICON_BASE + 'obsidian.md',                 'Produtividade'),
    CatalogEntry('logseq',      'Logseq',            'LQ', '#085b78', 'https://logseq.com/',                     'Notas e grafo de conhecimento',   _FAVICON_BASE + 'logseq.com',                  'Produtividade'),

    # ── Projetos ───────────────────────────────────────────────────────────────
    CatalogEntry('jira',        'Jira',              'JR', '#1f65bc', 'https://jira.atlassian.com/',             'Gestão de projetos Atlassian',    _FAVICON_BASE + 'jira.atlassian.com',          'Projetos'),
    CatalogEntry('linear',      'Linear',            'LN', '#5e6ad2', 'https://linear.app/',                     'Gestão de projetos moderna',      _FAVICON_BASE + 'linear.app',                  'Projetos'),
    CatalogEntry('asana',       'Asana',             'AS', '#ff5263', 'https://app.asana.com/',                  'Gestão de projetos',              _FAVICON_BASE + 'asana.com',                   'Projetos'),
    CatalogEntry('trello',      'Trello',            'TR', '#0052cc', 'https://trello.com/',                     'Kanban visual',                   _FAVICON_BASE + 'trello.com',                  'Projetos'),
    CatalogEntry('monday',      'Monday',            'MN', '#ff3d57', 'https://monday.com/',                     'Work OS',                         _FAVICON_BASE + 'monday.com',                  'Projetos'),
    CatalogEntry('clickup',     'ClickUp',           'CU', '#7b68ee', 'https://app.clickup.com/',                'Gestão de tarefas',               _FAVICON_BASE + 'clickup.com',                 'Projetos'),
    CatalogEntry('confluence',  'Confluence',        'CF', '#1f65bc', 'https://confluence.atlassian.com/',       'Wiki e documentação Atlassian',   _FAVICON_BASE + 'confluence.atlassian.com',    'Projetos'),
    CatalogEntry('basecamp',    'Basecamp',          'BC', '#1d2d35', 'https://basecamp.com/',                   'Gestão de projetos e equipes',    _FAVICON_BASE + 'basecamp.com',                'Projetos'),
    CatalogEntry('shortcut',    'Shortcut',          'SC', '#6515dd', 'https://app.shortcut.com/',               'Rastreamento de tarefas',         _FAVICON_BASE + 'shortcut.com',                'Projetos'),
    CatalogEntry('plane',       'Plane',             'PL', '#3f76ff', 'https://app.plane.so/',                   'Gestão open source',              _FAVICON_BASE + 'plane.so',                    'Projetos'),

    # ── Design ─────────────────────────────────────────────────────────────────
    CatalogEntry('figma',       'Figma',             'FG', '#a259ff', 'https://www.figma.com/',                  'Design colaborativo',             _FAVICON_BASE + 'figma.com',                   'Design'),
    CatalogEntry('miro',        'Miro',              'MI', '#ffdd57', 'https://miro.com/app/',                   'Quadro colaborativo',             _FAVICON_BASE + 'miro.com',                    'Design'),
    CatalogEntry('canva',       'Canva',             'CA', '#7d2ae7', 'https://www.canva.com/',                  'Design gráfico online',           _FAVICON_BASE + 'canva.com',                   'Design'),
    CatalogEntry('framer',      'Framer',            'FR', '#0055ff', 'https://www.framer.com/',                 'Design e prototipagem',           _FAVICON_BASE + 'framer.com',                  'Design'),
    CatalogEntry('whimsical',   'Whimsical',         'WH', '#a8a4ff', 'https://whimsical.com/',                  'Fluxogramas e wireframes',        _FAVICON_BASE + 'whimsical.com',               'Design'),
    CatalogEntry('zeplin',      'Zeplin',            'ZE', '#fdbd39', 'https://app.zeplin.io/',                  'Handoff de design',               _FAVICON_BASE + 'zeplin.io',                   'Design'),

    # ── Dev ────────────────────────────────────────────────────────────────────
    CatalogEntry('github',      'GitHub',            'GH', '#24292e', 'https://github.com/',                     'Código e repositórios',           _FAVICON_BASE + 'github.com',                  'Dev'),
    CatalogEntry('gitlab',      'GitLab',            'GL', '#fc6d26', 'https://gitlab.com/',                     'DevOps e repositórios',           _FAVICON_BASE + 'gitlab.com',                  'Dev'),
    CatalogEntry('bitbucket',   'Bitbucket',         'BB', '#0052cc', 'https://bitbucket.org/',                  'Git para equipes Atlassian',      _FAVICON_BASE + 'bitbucket.org',               'Dev'),
    CatalogEntry('stackoverflow','Stack Overflow',   'SO', '#f48024', 'https://stackoverflow.com/',              'Comunidade de desenvolvedores',   _FAVICON_BASE + 'stackoverflow.com',           'Dev'),
    CatalogEntry('replit',      'Replit',            'RP', '#f26207', 'https://replit.com/',                     'IDE online colaborativo',         _FAVICON_BASE + 'replit.com',                  'Dev'),
    CatalogEntry('vercel',      'Vercel',            'VC', '#000000', 'https://vercel.com/',                     'Deploy e hosting frontend',       _FAVICON_BASE + 'vercel.com',                  'Dev'),
    CatalogEntry('netlify',     'Netlify',           'NL', '#00c7b7', 'https://app.netlify.com/',                'Hosting e deploy automático',     _FAVICON_BASE + 'netlify.com',                 'Dev'),

    # ── CRM/Suporte ────────────────────────────────────────────────────────────
    CatalogEntry('hubspot',     'HubSpot',           'HS', '#ff7a59', 'https://app.hubspot.com/',                'CRM e marketing',                 _FAVICON_BASE + 'hubspot.com',                 'CRM/Suporte'),
    CatalogEntry('zendesk',     'Zendesk',           'ZD', '#03363d', 'https://www.zendesk.com/',                'Suporte ao cliente',              _FAVICON_BASE + 'zendesk.com',                 'CRM/Suporte'),
    CatalogEntry('freshdesk',   'Freshdesk',         'FD', '#25c16f', 'https://freshdesk.com/',                  'Helpdesk e suporte',              _FAVICON_BASE + 'freshdesk.com',               'CRM/Suporte'),
    CatalogEntry('intercom',    'Intercom',          'IC', '#1f8ded', 'https://app.intercom.com/',               'Suporte e engajamento',           _FAVICON_BASE + 'intercom.com',                'CRM/Suporte'),
    CatalogEntry('pipedrive',   'Pipedrive',         'PD', '#1a1a2e', 'https://app.pipedrive.com/',              'CRM de vendas',                   _FAVICON_BASE + 'pipedrive.com',               'CRM/Suporte'),

    # ── Google ─────────────────────────────────────────────────────────────────
    CatalogEntry('gcalendar',   'Google Agenda',     'GA', '#4285f4', 'https://calendar.google.com/',            'Calendário e reuniões',           _FAVICON_BASE + 'calendar.google.com',         'Google'),
    CatalogEntry('gmeet',       'Google Meet',       'MT', '#00ac47', 'https://meet.google.com/',                'Videoconferência Google',         _FAVICON_BASE + 'meet.google.com',             'Google'),
    CatalogEntry('gdrive',      'Google Drive',      'GD', '#4285f4', 'https://drive.google.com/',               'Armazenamento Google',            _FAVICON_BASE + 'drive.google.com',            'Google'),
    CatalogEntry('gdocs',       'Google Docs',       'GS', '#4285f4', 'https://docs.google.com/',                'Documentos colaborativos',        _FAVICON_BASE + 'docs.google.com',             'Google'),
    CatalogEntry('gkeep',       'Google Keep',       'GK', '#fbbc04', 'https://keep.google.com/',                'Notas rápidas Google',            _FAVICON_BASE + 'keep.google.com',             'Google'),

    # ── Microsoft ──────────────────────────────────────────────────────────────
    CatalogEntry('onedrive',    'OneDrive',          'OD', '#0078d4', 'https://onedrive.live.com/',              'Armazenamento Microsoft',         _FAVICON_BASE + 'onedrive.live.com',           'Microsoft'),
    CatalogEntry('sharepoint',  'SharePoint',        'SP', '#036ac4', 'https://sharepoint.com/',                 'Intranet e colaboração',          _FAVICON_BASE + 'sharepoint.com',              'Microsoft'),

    # ── IA ─────────────────────────────────────────────────────────────────────
    CatalogEntry('chatgpt',     'ChatGPT',           'GP', '#74aa9c', 'https://chat.openai.com/',                'IA conversacional OpenAI',        _FAVICON_BASE + 'chat.openai.com',             'IA'),
    CatalogEntry('claude',      'Claude',            'CL', '#d97706', 'https://claude.ai/',                      'IA conversacional Anthropic',     _FAVICON_BASE + 'claude.ai',                   'IA'),
    CatalogEntry('gemini',      'Gemini',            'GE', '#4285f4', 'https://gemini.google.com/',              'IA conversacional Google',        _FAVICON_BASE + 'gemini.google.com',           'IA'),
    CatalogEntry('perplexity',  'Perplexity',        'PX', '#20b2aa', 'https://www.perplexity.ai/',              'Busca com IA',                    _FAVICON_BASE + 'perplexity.ai',               'IA'),
    CatalogEntry('copilot',     'Copilot',           'CO', '#0078d4', 'https://copilot.microsoft.com/',          'IA Microsoft',                    _FAVICON_BASE + 'copilot.microsoft.com',       'IA'),
    CatalogEntry('mistral',     'Mistral',           'MI', '#ff7000', 'https://chat.mistral.ai/',                'IA open source francesa',         _FAVICON_BASE + 'mistral.ai',                  'IA'),
    CatalogEntry('poe',         'Poe',               'PO', '#6b4fbb', 'https://poe.com/',                        'Múltiplos modelos de IA',         _FAVICON_BASE + 'poe.com',                     'IA'),

    # ── Mídia/Social ───────────────────────────────────────────────────────────
    CatalogEntry('youtube',     'YouTube',           'YT', '#ff0000', 'https://www.youtube.com/',                'Vídeos e streaming',              _FAVICON_BASE + 'youtube.com',                 'Mídia/Social'),
    CatalogEntry('spotify',     'Spotify',           'SP', '#1db954', 'https://open.spotify.com/',               'Música e podcasts',               _FAVICON_BASE + 'spotify.com',                 'Mídia/Social'),
    CatalogEntry('twitter',     'Twitter/X',         'TW', '#000000', 'https://twitter.com/',                    'Rede social e notícias',          _FAVICON_BASE + 'twitter.com',                 'Mídia/Social'),
    CatalogEntry('linkedin',    'LinkedIn',          'LK', '#0a66c2', 'https://www.linkedin.com/',               'Rede profissional',               _FAVICON_BASE + 'linkedin.com',                'Mídia/Social'),
    CatalogEntry('reddit',      'Reddit',            'RD', '#ff4500', 'https://www.reddit.com/',                 'Fóruns e comunidades',            _FAVICON_BASE + 'reddit.com',                  'Mídia/Social'),
    CatalogEntry('twitch',      'Twitch',            'TC', '#9146ff', 'https://www.twitch.tv/',                  'Streaming de games',              _FAVICON_BASE + 'twitch.tv',                   'Mídia/Social'),
    CatalogEntry('mastodon',    'Mastodon',          'MD', '#6364ff', 'https://mastodon.social/',                'Rede social descentralizada',     _FAVICON_BASE + 'mastodon.social',             'Mídia/Social'),

    # ── Storage ────────────────────────────────────────────────────────────────
    CatalogEntry('dropbox',     'Dropbox',           'DB', '#0061ff', 'https://www.dropbox.com/',                'Armazenamento na nuvem',          _FAVICON_BASE + 'dropbox.com',                 'Storage'),
    CatalogEntry('box',         'Box',               'BX', '#0075c4', 'https://app.box.com/',                    'Armazenamento corporativo',       _FAVICON_BASE + 'box.com',                     'Storage'),

    # ── Personalizado ──────────────────────────────────────────────────────────
    CatalogEntry('custom',      'Personalizado',     '⚡', '#6c7086', 'https://',                                'Qualquer site ou webapp',         '',                                            'Personalizado'),
]


def get_entry(service_type: str) -> Optional[CatalogEntry]:
    return next((e for e in CATALOG if e.type == service_type), None)


def get_all_categories() -> List[str]:
    """Return sorted list of unique non-empty categories from the CATALOG."""
    seen = set()
    cats = []
    for e in CATALOG:
        if e.category and e.category not in seen:
            seen.add(e.category)
            cats.append(e.category)
    return sorted(cats)

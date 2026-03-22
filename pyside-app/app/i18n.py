"""
i18n.py — Internationalisation (i18n) support for Orbit.

Usage::

    from app.i18n import t, set_locale

    button.setText(t('add_service'))
    set_locale('pt')  # switch to Portuguese at runtime
"""
from __future__ import annotations

import locale as _locale_mod

# ---------------------------------------------------------------------------
# String catalogue
# ---------------------------------------------------------------------------

_STRINGS: dict[str, dict[str, str]] = {
    'en': {
        # -- General --
        'app_name':          'Orbit',
        'ok':                'OK',
        'cancel':            'Cancel',
        'save':              'Save',
        'close':             'Close',
        'remove':            'Remove',
        'add':               'Add',
        'back':              'Back',
        'configure':         'Configure',
        'confirm':           'Confirm',
        # -- Services --
        'add_service':       'Add Service',
        'remove_service':    'Remove Service',
        'configure_service': 'Configure Service',
        'enable_service':    'Enable Service',
        'disable_service':   'Disable Service',
        'open_in_window':    'Open in Window',
        'add_account':       'Add Account',
        'search_services':   'Search services...',
        'no_services':       'No services found',
        # -- Workspace --
        'workspace':         'Workspace',
        'new_workspace':     'New Workspace',
        'switch_workspace':  'Switch Workspace',
        'rename_workspace':  'Rename Workspace',
        'delete_workspace':  'Delete Workspace',
        # -- Notifications / DND --
        'do_not_disturb':    'Do Not Disturb',
        'notifications':     'Notifications',
        'notif_history':     'Notification History',
        'clear_history':     'Clear History',
        # -- Sidebar --
        'compact_sidebar':   'Toggle compact sidebar',
        'focus_mode':        'Focus mode',
        # -- Focus profiles --
        'focus_profile':     'Focus Profile',
        'profile_default':   '🌐 Default',
        'profile_work':      '💼 Work',
        'profile_personal':  '🏠 Personal',
        'profile_off':       '🔕 Off',
        # -- Settings --
        'settings':          'Settings',
        'theme':             'Theme',
        'language':          'Language',
        'shortcuts':         'Keyboard Shortcuts',
        # -- Tags --
        'tags':              'Tags (comma-separated)',
        'no_tags':           'No tags',
        # -- Audit --
        'audit_log':         'Audit Log',
        'view_audit_log':    'View Audit Log',
        # -- Clipboard --
        'clipboard_cleared': 'Clipboard cleared',
        # -- Lock --
        'lock_now':          'Lock Now',
        'configure_pin':     'Configure PIN...',
        # -- Misc --
        'show_orbit':        'Show Orbit',
        'quit':              'Quit Orbit',
        'statistics':        'Statistics',
        'portable_mode':     'PORTABLE',
    },
    'pt': {
        # -- General --
        'app_name':          'Orbit',
        'ok':                'OK',
        'cancel':            'Cancelar',
        'save':              'Salvar',
        'close':             'Fechar',
        'remove':            'Remover',
        'add':               'Adicionar',
        'back':              'Voltar',
        'configure':         'Configurar',
        'confirm':           'Confirmar',
        # -- Services --
        'add_service':       'Adicionar Serviço',
        'remove_service':    'Remover Serviço',
        'configure_service': 'Configurar Serviço',
        'enable_service':    'Habilitar Serviço',
        'disable_service':   'Desabilitar Serviço',
        'open_in_window':    'Abrir em janela',
        'add_account':       'Adicionar conta',
        'search_services':   'Pesquisar serviços...',
        'no_services':       'Nenhum serviço encontrado',
        # -- Workspace --
        'workspace':         'Espaço de Trabalho',
        'new_workspace':     'Novo Espaço de Trabalho',
        'switch_workspace':  'Trocar Workspace',
        'rename_workspace':  'Renomear Workspace',
        'delete_workspace':  'Excluir Workspace',
        # -- Notifications / DND --
        'do_not_disturb':    'Não perturbe',
        'notifications':     'Notificações',
        'notif_history':     'Histórico de notificações',
        'clear_history':     'Limpar histórico',
        # -- Sidebar --
        'compact_sidebar':   'Alternar sidebar compacta',
        'focus_mode':        'Modo foco',
        # -- Focus profiles --
        'focus_profile':     'Perfil de Foco',
        'profile_default':   '🌐 Padrão',
        'profile_work':      '💼 Trabalho',
        'profile_personal':  '🏠 Pessoal',
        'profile_off':       '🔕 Offline',
        # -- Settings --
        'settings':          'Configurações',
        'theme':             'Tema',
        'language':          'Idioma',
        'shortcuts':         'Atalhos de teclado',
        # -- Tags --
        'tags':              'Tags (separadas por vírgula)',
        'no_tags':           'Sem tags',
        # -- Audit --
        'audit_log':         'Log de Auditoria',
        'view_audit_log':    'Ver Log de Auditoria',
        # -- Clipboard --
        'clipboard_cleared': 'Área de transferência limpa',
        # -- Lock --
        'lock_now':          'Bloquear agora',
        'configure_pin':     'Configurar PIN...',
        # -- Misc --
        'show_orbit':        'Mostrar Orbit',
        'quit':              'Fechar Orbit',
        'statistics':        'Estatísticas',
        'portable_mode':     'PORTÁTIL',
    },
}

# ---------------------------------------------------------------------------
# Active locale — auto-detected, overridable
# ---------------------------------------------------------------------------

def _detect_locale() -> str:
    """Return 'pt' if the system locale is Portuguese, else 'en'."""
    try:
        loc = _locale_mod.getdefaultlocale()[0] or ''
        if loc.lower().startswith('pt'):
            return 'pt'
    except Exception:
        pass
    return 'en'


LOCALE: str = _detect_locale()


def get_locale() -> str:
    """Return the currently active locale code ('en' or 'pt')."""
    return LOCALE


def set_locale(loc: str) -> None:
    """
    Switch the active locale.

    Parameters
    ----------
    loc:
        Locale code ('en' or 'pt').  Unknown codes fall back to 'en'.
    """
    global LOCALE
    LOCALE = loc if loc in _STRINGS else 'en'


def t(key: str) -> str:
    """
    Translate *key* using the active locale.

    Falls back to the English string if the key is missing in the active locale,
    and returns the key itself if the key is not found anywhere.
    """
    catalogue = _STRINGS.get(LOCALE, _STRINGS['en'])
    if key in catalogue:
        return catalogue[key]
    # Fallback to English
    return _STRINGS['en'].get(key, key)


def available_locales() -> list[str]:
    """Return a list of available locale codes."""
    return list(_STRINGS.keys())

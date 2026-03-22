export type HealthState = 'healthy' | 'warning' | 'offline'
export type NotificationMode = 'native' | 'muted' | 'mentions'

export type ChatAccount = {
  id: string
  label: string
  workspace: string
  profile: string
  serviceUrl: string
  health: HealthState
  notifications: NotificationMode
  lastSync: string
}

export type HibernateAfter = 5 | 15 | 30 | 60 | null

export type ChatService = {
  id: string
  serviceType: string
  name: string
  icon: string
  color: string
  status: HealthState
  unread: number
  pinned: boolean
  hibernateAfter: HibernateAfter
  accounts: ChatAccount[]
}

export type WorkspacePreferences = {
  compactRail: boolean
  showTelemetry: boolean
  focusMode: boolean
  restoreLiveSessions: boolean
}

export type WorkspaceSnapshot = {
  version: 1
  activeServiceId: string
  activeAccountId: string
  search: string
  liveAccountIds: string[]
  preferences: WorkspacePreferences
  services: ChatService[]
}

export const seedWorkspace: WorkspaceSnapshot = {
  version: 1,
  activeServiceId: 'slack',
  activeAccountId: 'slack-hdx',
  search: '',
  liveAccountIds: [],
  preferences: {
    compactRail: false,
    showTelemetry: true,
    focusMode: false,
    restoreLiveSessions: true,
  },
  services: [
    {
      id: 'slack',
      serviceType: 'slack',
      name: 'Slack',
      icon: 'SL',
      color: '#d46d2a',
      status: 'healthy',
      unread: 18,
      pinned: true,
      hibernateAfter: null,
      accounts: [
        {
          id: 'slack-hdx',
          label: 'HDX Core',
          workspace: 'hdx-core',
          profile: 'profile://slack/hdx-core',
          serviceUrl: 'https://app.slack.com/client/T-HDX',
          health: 'healthy',
          notifications: 'mentions',
          lastSync: '2 min',
        },
        {
          id: 'slack-labs',
          label: 'Labs',
          workspace: 'hdx-labs',
          profile: 'profile://slack/hdx-labs',
          serviceUrl: 'https://app.slack.com/client/T-LABS',
          health: 'warning',
          notifications: 'native',
          lastSync: '11 min',
        },
      ],
    },
    {
      id: 'whatsapp',
      serviceType: 'whatsapp',
      name: 'WhatsApp',
      icon: 'WA',
      color: '#2e936d',
      status: 'healthy',
      unread: 6,
      pinned: true,
      hibernateAfter: null,
      accounts: [
        {
          id: 'wa-personal',
          label: 'Pessoal',
          workspace: 'personal',
          profile: 'profile://whatsapp/pessoal',
          serviceUrl: 'https://web.whatsapp.com/',
          health: 'healthy',
          notifications: 'native',
          lastSync: 'agora',
        },
        {
          id: 'wa-support',
          label: 'Suporte',
          workspace: 'support',
          profile: 'profile://whatsapp/suporte',
          serviceUrl: 'https://web.whatsapp.com/',
          health: 'healthy',
          notifications: 'native',
          lastSync: '1 min',
        },
      ],
    },
    {
      id: 'discord',
      serviceType: 'discord',
      name: 'Discord',
      icon: 'DC',
      color: '#456ae6',
      status: 'warning',
      unread: 3,
      pinned: false,
      hibernateAfter: null,
      accounts: [
        {
          id: 'discord-ops',
          label: 'Ops',
          workspace: 'ops-guild',
          profile: 'profile://discord/ops',
          serviceUrl: 'https://discord.com/app',
          health: 'warning',
          notifications: 'mentions',
          lastSync: '5 min',
        },
      ],
    },
    {
      id: 'gmail',
      serviceType: 'gmail',
      name: 'Gmail',
      icon: 'GM',
      color: '#b95d4b',
      status: 'offline',
      unread: 24,
      pinned: false,
      hibernateAfter: null,
      accounts: [
        {
          id: 'gmail-finance',
          label: 'Financeiro',
          workspace: 'finance',
          profile: 'profile://gmail/finance',
          serviceUrl: 'https://mail.google.com/mail/u/0/#inbox',
          health: 'offline',
          notifications: 'muted',
          lastSync: '39 min',
        },
      ],
    },
  ],
}


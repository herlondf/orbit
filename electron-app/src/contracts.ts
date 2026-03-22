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
  activeServiceId: '',
  activeAccountId: '',
  search: '',
  liveAccountIds: [],
  preferences: {
    compactRail: false,
    showTelemetry: true,
    focusMode: false,
    restoreLiveSessions: true,
  },
  services: [],
}


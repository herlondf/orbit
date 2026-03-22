import { seedWorkspace, type ChatService, type WorkspaceSnapshot } from './contracts'

const STORAGE_KEY = 'octochat.workspace.v1'

function isWorkspaceSnapshot(value: unknown): value is WorkspaceSnapshot {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Partial<WorkspaceSnapshot>
  return (
    candidate.version === 1 &&
    typeof candidate.activeServiceId === 'string' &&
    typeof candidate.activeAccountId === 'string' &&
    typeof candidate.search === 'string' &&
    Array.isArray(candidate.liveAccountIds) &&
    Array.isArray(candidate.services) &&
    !!candidate.preferences
  )
}

function migrateService(service: ChatService): ChatService {
  return {
    ...service,
    serviceType: service.serviceType ?? service.id,
    hibernateAfter: service.hibernateAfter ?? null,
  }
}

function migrateSnapshot(snapshot: WorkspaceSnapshot): WorkspaceSnapshot {
  return {
    ...snapshot,
    services: snapshot.services.map(migrateService),
  }
}

export function loadWorkspaceSnapshot(): WorkspaceSnapshot {
  if (typeof window === 'undefined') {
    return seedWorkspace
  }

  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return seedWorkspace
  }

  try {
    const parsed = JSON.parse(raw) as unknown
    if (isWorkspaceSnapshot(parsed)) {
      return migrateSnapshot(parsed)
    }
  } catch {
    window.localStorage.removeItem(STORAGE_KEY)
  }

  return seedWorkspace
}

export function saveWorkspaceSnapshot(snapshot: WorkspaceSnapshot): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
}

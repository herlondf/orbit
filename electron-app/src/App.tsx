import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { on } from './ipc'
import './App.css'
import { type ServiceCatalogEntry, serviceCatalog } from './catalog'
import {
  type ChatAccount,
  type ChatService,
  type HibernateAfter,
  type WorkspaceSnapshot,
} from './contracts'
import { ensureTray, pushDesktopNotification } from './desktopShell'
import { loadWorkspaceSnapshot, saveWorkspaceSnapshot } from './storage'
import {
  accountLabel,
  closeWebview,
  createEmbeddedWebview,
  hideWebview,
  openWebviewDevtools,
  setWebviewBounds,
  showWebview,
} from './serviceHost'

// ─── types ────────────────────────────────────────────────────────────────────

type ToastEntry = {
  id: string
  serviceId: string
  serviceIcon: string
  serviceColor: string
  serviceName: string
  title: string
  body: string
}

type CtxMenu = { serviceId: string; x: number; y: number }

// ─── components ───────────────────────────────────────────────────────────────

function ToastList({ toasts, onDismiss, onActivate }: {
  toasts: ToastEntry[]
  onDismiss: (id: string) => void
  onActivate: (serviceId: string) => void
}) {
  if (toasts.length === 0) return null
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className="toast" onClick={() => { onActivate(t.serviceId); onDismiss(t.id) }}>
          <div className="toast-icon" style={{ background: t.serviceColor }}>{t.serviceIcon}</div>
          <div className="toast-text">
            <span className="toast-svc">{t.serviceName}</span>
            <span className="toast-title">{t.title}</span>
            {t.body && <span className="toast-body">{t.body}</span>}
          </div>
          <button className="toast-close" onClick={(e) => { e.stopPropagation(); onDismiss(t.id) }}>✕</button>
        </div>
      ))}
    </div>
  )
}

function ContextMenu({ menu, onClose, onConfig, onAddAccount, onRemove }: {
  menu: CtxMenu
  onClose: () => void
  onConfig: () => void
  onAddAccount: () => void
  onRemove: () => void
}) {
  return (
    <>
      <div className="ctx-overlay" onClick={onClose} onContextMenu={(e) => { e.preventDefault(); onClose() }} />
      <div className="ctx-menu" style={{ left: menu.x, top: menu.y }}>
        <button className="ctx-item" onClick={() => { onConfig(); onClose() }}>⚙&ensp;Configurar</button>
        <button className="ctx-item" onClick={() => { onAddAccount(); onClose() }}>+&ensp;Adicionar conta</button>
        <div className="ctx-sep" />
        <button className="ctx-item danger" onClick={() => { onRemove(); onClose() }}>🗑&ensp;Remover serviço</button>
      </div>
    </>
  )
}

function ConfirmModal({ message, onConfirm, onCancel }: {
  message: string
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="modal-overlay">
      <div className="modal-box" style={{ width: 380, gap: 20 }}>
        <p className="modal-title">Confirmar</p>
        <p style={{ fontSize: 14, color: '#cdd6f4', lineHeight: 1.6 }}>{message}</p>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onCancel}>Cancelar</button>
          <button className="btn btn-danger" onClick={onConfirm}>Remover</button>
        </div>
      </div>
    </div>
  )
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function uniqueId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
}

function slugify(v: string): string {
  return v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot>(() => loadWorkspaceSnapshot())
  const [activeServiceId, setActiveServiceId] = useState<string | null>(
    () => loadWorkspaceSnapshot().activeServiceId || null,
  )
  const [activeAccountId, setActiveAccountId] = useState<string | null>(
    () => loadWorkspaceSnapshot().activeAccountId || null,
  )

  // Modals
  const [showAddModal, setShowAddModal] = useState(false)
  const [catalogEntry, setCatalogEntry] = useState<ServiceCatalogEntry | null>(null)
  const [addLabel, setAddLabel] = useState('')
  const [addUrl, setAddUrl] = useState('')
  const [addAccountSvcId, setAddAccountSvcId] = useState<string | null>(null)
  const [addAccountLabel, setAddAccountLabel] = useState('')
  const [addAccountUrl, setAddAccountUrl] = useState('')

  // UI state
  const [configServiceId, setConfigServiceId] = useState<string | null>(null)
  const [ctxMenu, setCtxMenu] = useState<CtxMenu | null>(null)
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const [confirmDialog, setConfirmDialog] = useState<{ message: string; resolve: (v: boolean) => void } | null>(null)

  // Refs
  const openedLabels = useRef(new Set<string>())
  const webviewAreaRef = useRef<HTMLDivElement>(null)
  const lastFocusedAt = useRef(new Map<string, number>())
  const workspaceRef = useRef(workspace)
  workspaceRef.current = workspace

  const activeServiceIdRef = useRef(activeServiceId)
  activeServiceIdRef.current = activeServiceId

  // ── derived ──────────────────────────────────────────────────────────────────

  const activeService = useMemo(
    () => workspace.services.find((s) => s.id === activeServiceId) ?? null,
    [workspace.services, activeServiceId],
  )
  const activeAccount = useMemo(
    () =>
      activeService?.accounts.find((a) => a.id === activeAccountId) ??
      activeService?.accounts[0] ??
      null,
    [activeService, activeAccountId],
  )

  const activeAccountRef = useRef(activeAccount)
  activeAccountRef.current = activeAccount

  const serviceByLabelRef = useRef(new Map<string, ChatService>())
  serviceByLabelRef.current = useMemo(() => {
    const map = new Map<string, ChatService>()
    for (const svc of workspace.services)
      for (const acc of svc.accounts) map.set(accountLabel(acc), svc)
    return map
  }, [workspace.services])

  // Any modal open → hide webviews (WebContentsView native controls always render above DOM)
  const anyModalOpen = showAddModal || !!addAccountSvcId || !!confirmDialog || !!ctxMenu

  // ── showConfirm helper ────────────────────────────────────────────────────────

  const showConfirm = useCallback((message: string): Promise<boolean> =>
    new Promise<boolean>((resolve) => setConfirmDialog({ message, resolve }))
  , [])

  // ── persist ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    saveWorkspaceSnapshot({
      ...workspace,
      activeServiceId: activeServiceId ?? '',
      activeAccountId: activeAccountId ?? '',
    })
  }, [workspace, activeServiceId, activeAccountId])

  // ── tray ──────────────────────────────────────────────────────────────────────

  useEffect(() => {
    void ensureTray(() => {}).catch(() => {})
  }, [])

  // ── F12: open DevTools for the active webview ─────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'F12') {
        const acc = activeAccountRef.current
        if (acc) void openWebviewDevtools(accountLabel(acc)).catch(() => {})
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── hide/restore webviews when modal opens/closes ─────────────────────────────

  useEffect(() => {
    if (anyModalOpen) {
      for (const lbl of openedLabels.current) void hideWebview(lbl).catch(() => {})
    } else {
      const acc = activeAccountRef.current
      if (acc) {
        const lbl = accountLabel(acc)
        if (openedLabels.current.has(lbl)) void showWebview(lbl).catch(() => {})
      }
    }
  }, [anyModalOpen])

  // ── webview bounds: resize observer ───────────────────────────────────────────

  const getBounds = useCallback(() => {
    const el = webviewAreaRef.current
    if (!el) return null
    const r = el.getBoundingClientRect()
    return {
      x: Math.round(r.left),
      y: Math.round(r.top),
      width: Math.round(r.width),
      height: Math.round(r.height),
    }
  }, [])

  useEffect(() => {
    const el = webviewAreaRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      const b = getBounds()
      if (!b) return
      for (const lbl of openedLabels.current)
        void setWebviewBounds(lbl, b.x, b.y, b.width, b.height).catch(() => {})
    })
    ro.observe(el)
    return () => ro.disconnect()
  })

  // ── account activation ────────────────────────────────────────────────────────

  const handleSelectAccount = useCallback(
    async (account: ChatAccount) => {
      const lbl = accountLabel(account)
      lastFocusedAt.current.set(account.id, Date.now())

      const b = getBounds()
      if (!openedLabels.current.has(lbl)) {
        if (b) {
          // Fire and forget — main process loads URL asynchronously
          createEmbeddedWebview(account, b.x, b.y, b.width, b.height).catch(() => {})
          openedLabels.current.add(lbl)
          setWorkspace((ws) => ({
            ...ws,
            liveAccountIds: Array.from(new Set([...ws.liveAccountIds, account.id])),
          }))
        }
      } else if (b) {
        await setWebviewBounds(lbl, b.x, b.y, b.width, b.height).catch(() => {})
      }

      for (const other of openedLabels.current)
        if (other !== lbl) await hideWebview(other).catch(() => {})
      if (openedLabels.current.has(lbl)) await showWebview(lbl).catch(() => {})

      setActiveAccountId(account.id)
    },
    [getBounds],
  )

  const handleSelectService = useCallback(
    (service: ChatService) => {
      setActiveServiceId(service.id)
      setConfigServiceId(null)
      setCtxMenu(null)
      const first = service.accounts[0]
      if (first) void handleSelectAccount(first)
    },
    [handleSelectAccount],
  )

  const prevServiceId = useRef<string | null>(null)
  useEffect(() => {
    if (!activeService || !activeAccount) return
    if (activeService.id === prevServiceId.current) return
    prevServiceId.current = activeService.id
    if (!openedLabels.current.has(accountLabel(activeAccount))) {
      const t = window.setTimeout(() => void handleSelectAccount(activeAccount), 50)
      return () => window.clearTimeout(t)
    }
  }, [activeService, activeAccount, handleSelectAccount])

  // ── toast helper ──────────────────────────────────────────────────────────────

  const addToast = useCallback((entry: Omit<ToastEntry, 'id'>) => {
    const id = uniqueId()
    setToasts((prev) => [...prev.slice(-4), { ...entry, id }])
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 6_000)
  }, [])

  const addToastRef = useRef(addToast)
  addToastRef.current = addToast

  // ── event listeners ───────────────────────────────────────────────────────────

  useEffect(() => {
    // Badge counts from service pages (title-based or preload injection)
    const offBadge = on<{ label: string; count: number }>('webview:badge', ({ label, count }) => {
      setWorkspace((ws) => ({
        ...ws,
        services: ws.services.map((s) => {
          const owns = s.accounts.some((a) => accountLabel(a) === label)
          return owns ? { ...s, unread: count } : s
        }),
      }))
    })

    // Notifications intercepted from service pages by the service preload
    const offNotify = on<{ label: string; title: string; body: string }>(
      'webview:notify',
      ({ label, title, body }) => {
        void pushDesktopNotification(title, body).catch(() => {})
        const svc = serviceByLabelRef.current.get(label)
        if (svc) {
          addToastRef.current({
            serviceId: svc.id,
            serviceIcon: svc.icon,
            serviceColor: svc.color,
            serviceName: svc.name,
            title,
            body,
          })
        }
      },
    )

    return () => {
      offBadge()
      offNotify()
    }
  }, [])

  // ── hibernate ─────────────────────────────────────────────────────────────────

  useEffect(() => {
    const id = window.setInterval(async () => {
      const ws = workspaceRef.current
      const now = Date.now()
      for (const svc of ws.services) {
        if (!svc.hibernateAfter) continue
        const threshold = svc.hibernateAfter * 60_000
        for (const acc of svc.accounts) {
          if (!ws.liveAccountIds.includes(acc.id)) continue
          const last = lastFocusedAt.current.get(acc.id)
          if (!last || now - last <= threshold) continue
          const lbl = accountLabel(acc)
          lastFocusedAt.current.delete(acc.id)
          openedLabels.current.delete(lbl)
          await closeWebview(lbl).catch(() => {})
          setWorkspace((cur) => ({
            ...cur,
            liveAccountIds: cur.liveAccountIds.filter((x) => x !== acc.id),
          }))
        }
      }
    }, 5_000)
    return () => window.clearInterval(id)
  }, [])

  // ── add / remove service ──────────────────────────────────────────────────────

  function handleAddService(e: React.FormEvent) {
    e.preventDefault()
    if (!catalogEntry) return
    const id = `${catalogEntry.type}-${uniqueId()}`
    const accountId = `${id}-acc`
    const newService: ChatService = {
      id,
      serviceType: catalogEntry.type,
      name: addLabel.trim() || catalogEntry.name,
      icon: catalogEntry.icon,
      color: catalogEntry.color,
      status: 'healthy',
      unread: 0,
      pinned: false,
      hibernateAfter: null,
      accounts: [{
        id: accountId,
        label: addLabel.trim() || catalogEntry.name,
        workspace: addLabel.trim() || catalogEntry.name,
        profile: `profile://${catalogEntry.type}/${slugify(addLabel || catalogEntry.name)}`,
        serviceUrl: addUrl.trim() || catalogEntry.defaultUrl,
        health: 'healthy',
        notifications: 'native',
        lastSync: '-',
      }],
    }
    setWorkspace((ws) => ({ ...ws, services: [...ws.services, newService] }))
    setShowAddModal(false)
    setCatalogEntry(null)
    setActiveServiceId(newService.id)
    setActiveAccountId(accountId)
  }

  async function handleRemoveService(service: ChatService) {
    if (!await showConfirm(`Remover "${service.name}" e todas as contas?`)) return
    for (const acc of service.accounts) {
      const lbl = accountLabel(acc)
      openedLabels.current.delete(lbl)
      await closeWebview(lbl).catch(() => {})
    }
    setWorkspace((ws) => ({
      ...ws,
      services: ws.services.filter((s) => s.id !== service.id),
      liveAccountIds: ws.liveAccountIds.filter((id) => !service.accounts.some((a) => a.id === id)),
    }))
    if (activeServiceId === service.id) {
      const remaining = workspace.services.filter((s) => s.id !== service.id)
      setActiveServiceId(remaining[0]?.id ?? null)
      setActiveAccountId(null)
    }
    if (configServiceId === service.id) setConfigServiceId(null)
  }

  // ── add / remove account ──────────────────────────────────────────────────────

  function handleAddAccount(e: React.FormEvent, svc: ChatService) {
    e.preventDefault()
    if (!addAccountLabel.trim()) return
    const accountId = `${svc.id}-${uniqueId()}`
    const newAccount: ChatAccount = {
      id: accountId,
      label: addAccountLabel.trim(),
      workspace: addAccountLabel.trim(),
      profile: `profile://${svc.serviceType}/${slugify(addAccountLabel)}`,
      serviceUrl: addAccountUrl.trim() || svc.accounts[0]?.serviceUrl || '',
      health: 'healthy',
      notifications: 'native',
      lastSync: '-',
    }
    setWorkspace((ws) => ({
      ...ws,
      services: ws.services.map((s) =>
        s.id === svc.id ? { ...s, accounts: [...s.accounts, newAccount] } : s,
      ),
    }))
    setAddAccountSvcId(null)
    void handleSelectAccount(newAccount)
  }

  async function handleRemoveAccount(svc: ChatService, acc: ChatAccount) {
    if (!await showConfirm(`Remover conta "${acc.label}"?`)) return
    const lbl = accountLabel(acc)
    openedLabels.current.delete(lbl)
    await closeWebview(lbl).catch(() => {})
    setWorkspace((ws) => ({
      ...ws,
      services: ws.services.map((s) =>
        s.id === svc.id ? { ...s, accounts: s.accounts.filter((a) => a.id !== acc.id) } : s,
      ),
      liveAccountIds: ws.liveAccountIds.filter((id) => id !== acc.id),
    }))
    if (activeAccountId === acc.id) {
      const remaining = svc.accounts.filter((a) => a.id !== acc.id)
      if (remaining[0]) void handleSelectAccount(remaining[0])
      else setActiveAccountId(null)
    }
  }

  function updateServiceConfig(svcId: string, patch: Partial<Pick<ChatService, 'name' | 'hibernateAfter'>>) {
    setWorkspace((ws) => ({
      ...ws,
      services: ws.services.map((s) => (s.id === svcId ? { ...s, ...patch } : s)),
    }))
  }

  // ── render ────────────────────────────────────────────────────────────────────

  const configService = workspace.services.find((s) => s.id === configServiceId) ?? null
  const ctxService = ctxMenu ? (workspace.services.find((s) => s.id === ctxMenu.serviceId) ?? null) : null

  return (
    <div className="app-shell" onClick={() => setCtxMenu(null)}>

      {/* ── SIDEBAR ───────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">🐙</div>

        <nav className="sidebar-services">
          {workspace.services.map((svc) => (
            <button
              key={svc.id}
              className={`service-btn${activeServiceId === svc.id ? ' active' : ''}`}
              title={svc.name}
              onClick={(e) => { e.stopPropagation(); handleSelectService(svc) }}
              onContextMenu={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setCtxMenu({ serviceId: svc.id, x: e.clientX, y: e.clientY })
              }}
            >
              <div className="service-icon" style={{ background: svc.color }}>{svc.icon}</div>
              {svc.unread > 0 && (
                <span className="unread-badge">{svc.unread > 99 ? '99+' : svc.unread}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button
            className="sidebar-action add"
            title="Adicionar serviço"
            onClick={(e) => { e.stopPropagation(); setShowAddModal(true); setCatalogEntry(null) }}
          >
            +
          </button>
        </div>
      </aside>

      {/* ── CONTENT ───────────────────────────────────────────────────────── */}
      <div className="content-area">
        {activeService ? (
          <>
            <header className="content-header">
              <div className="service-icon sm" style={{ background: activeService.color }}>
                {activeService.icon}
              </div>
              <span className="content-service-name">{activeService.name}</span>

              <div className="account-tabs">
                {activeService.accounts.map((acc) => (
                  <button
                    key={acc.id}
                    className={`account-tab${acc.id === (activeAccount?.id ?? '') ? ' active' : ''}`}
                    onClick={() => void handleSelectAccount(acc)}
                  >
                    {acc.label}
                  </button>
                ))}
              </div>

              <div className="header-actions">
                <button
                  className="header-btn"
                  title="Adicionar conta"
                  onClick={() => {
                    setAddAccountSvcId(activeService.id)
                    setAddAccountLabel('')
                    setAddAccountUrl(activeService.accounts[0]?.serviceUrl ?? '')
                  }}
                >+</button>
                <button
                  className={`header-btn${configServiceId === activeService.id ? ' active-btn' : ''}`}
                  title="Configurar"
                  onClick={() => setConfigServiceId(configServiceId === activeService.id ? null : activeService.id)}
                >⚙</button>
                <button
                  className="header-btn"
                  title="Abrir DevTools (F12)"
                  onClick={() => activeAccount && void openWebviewDevtools(accountLabel(activeAccount)).catch(() => {})}
                >🔍</button>
                <button
                  className="header-btn danger"
                  title="Remover serviço"
                  onClick={() => void handleRemoveService(activeService)}
                >🗑</button>
              </div>

              {configService?.id === activeService.id && (
                <div className="config-panel">
                  <div className="form-field">
                    <label>Nome</label>
                    <input
                      value={configService.name}
                      onChange={(e) => updateServiceConfig(configService.id, { name: e.target.value })}
                    />
                  </div>
                  <div className="form-field">
                    <label>Hibernar após inatividade</label>
                    <select
                      value={configService.hibernateAfter ?? ''}
                      onChange={(e) =>
                        updateServiceConfig(configService.id, {
                          hibernateAfter: e.target.value ? (Number(e.target.value) as HibernateAfter) : null,
                        })
                      }
                    >
                      <option value="">Nunca</option>
                      <option value="5">5 min</option>
                      <option value="15">15 min</option>
                      <option value="30">30 min</option>
                      <option value="60">1 hora</option>
                    </select>
                  </div>
                  {activeAccount && (
                    <button
                      className="btn btn-danger"
                      style={{ marginTop: 4 }}
                      onClick={() => void handleRemoveAccount(activeService, activeAccount)}
                    >Remover conta ativa</button>
                  )}
                </div>
              )}
            </header>

            <div className="webview-area" ref={webviewAreaRef}>
              {activeAccount && !openedLabels.current.has(accountLabel(activeAccount)) && (
                <div className="webview-placeholder">
                  <div className="service-icon lg" style={{ background: activeService.color }}>
                    {activeService.icon}
                  </div>
                  <p>{activeService.name} — {activeAccount.label}</p>
                  <button className="btn btn-primary" onClick={() => void handleSelectAccount(activeAccount)}>
                    Abrir
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="welcome-screen">
            <div className="logo">🐙</div>
            <h2>OctoChat</h2>
            <p>Adicione um serviço para começar.<br />Suporta Slack, WhatsApp, Telegram, Gmail e mais.</p>
            <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
              + Adicionar serviço
            </button>
          </div>
        )}
      </div>

      {/* ── CONTEXT MENU ──────────────────────────────────────────────────── */}
      {ctxMenu && ctxService && (
        <ContextMenu
          menu={ctxMenu}
          onClose={() => setCtxMenu(null)}
          onConfig={() => { setConfigServiceId(ctxService.id); handleSelectService(ctxService) }}
          onAddAccount={() => {
            setAddAccountSvcId(ctxService.id)
            setAddAccountLabel('')
            setAddAccountUrl(ctxService.accounts[0]?.serviceUrl ?? '')
          }}
          onRemove={() => void handleRemoveService(ctxService)}
        />
      )}

      {/* ── ADD SERVICE MODAL ─────────────────────────────────────────────── */}
      {showAddModal && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowAddModal(false) }}>
          <div className="modal-box">
            <p className="modal-title">{catalogEntry ? `Configurar ${catalogEntry.name}` : 'Escolha um serviço'}</p>
            {!catalogEntry ? (
              <>
                <div className="catalog-grid">
                  {serviceCatalog.map((entry) => (
                    <button
                      key={entry.type}
                      className="catalog-card"
                      onClick={() => { setCatalogEntry(entry); setAddUrl(entry.defaultUrl); setAddLabel(entry.name) }}
                    >
                      <div className="catalog-icon" style={{ background: entry.color }}>{entry.icon}</div>
                      <span className="catalog-name">{entry.name}</span>
                    </button>
                  ))}
                </div>
                <div className="modal-actions">
                  <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancelar</button>
                </div>
              </>
            ) : (
              <form className="modal-form" onSubmit={handleAddService}>
                <div className="form-field">
                  <label>Nome / apelido</label>
                  <input value={addLabel} onChange={(e) => setAddLabel(e.target.value)} placeholder={catalogEntry.name} autoFocus />
                </div>
                <div className="form-field">
                  <label>URL</label>
                  <input value={addUrl} onChange={(e) => setAddUrl(e.target.value)} placeholder={catalogEntry.defaultUrl} required />
                </div>
                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setCatalogEntry(null)}>← Voltar</button>
                  <button type="submit" className="btn btn-primary">Adicionar</button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── ADD ACCOUNT MODAL ─────────────────────────────────────────────── */}
      {addAccountSvcId && (() => {
        const svc = workspace.services.find((s) => s.id === addAccountSvcId)
        if (!svc) return null
        return (
          <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setAddAccountSvcId(null) }}>
            <div className="modal-box">
              <p className="modal-title">Adicionar conta — {svc.name}</p>
              <form className="modal-form" onSubmit={(e) => handleAddAccount(e, svc)}>
                <div className="form-field">
                  <label>Nome da conta</label>
                  <input value={addAccountLabel} onChange={(e) => setAddAccountLabel(e.target.value)} placeholder="ex: Trabalho, Pessoal" autoFocus required />
                </div>
                <div className="form-field">
                  <label>URL</label>
                  <input value={addAccountUrl} onChange={(e) => setAddAccountUrl(e.target.value)} required />
                </div>
                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setAddAccountSvcId(null)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary">Adicionar</button>
                </div>
              </form>
            </div>
          </div>
        )
      })()}

      {/* ── TOAST NOTIFICATIONS ───────────────────────────────────────────── */}
      <ToastList
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
        onActivate={(serviceId) => {
          const svc = workspace.services.find((s) => s.id === serviceId)
          if (svc) handleSelectService(svc)
        }}
      />

      {/* ── CONFIRM DIALOG ────────────────────────────────────────────────── */}
      {confirmDialog && (
        <ConfirmModal
          message={confirmDialog.message}
          onConfirm={() => { confirmDialog.resolve(true); setConfirmDialog(null) }}
          onCancel={() => { confirmDialog.resolve(false); setConfirmDialog(null) }}
        />
      )}
    </div>
  )
}

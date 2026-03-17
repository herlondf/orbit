import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import {
  seedWorkspace,
  type ChatAccount,
  type ChatService,
  type NotificationMode,
  type WorkspaceSnapshot,
} from './contracts'
import { ensureTray, pushDesktopNotification } from './desktopShell'
import { loadWorkspaceSnapshot, saveWorkspaceSnapshot } from './storage'
import {
  accountLabel,
  closeAccountWebview,
  closeAccountWebviews,
  listAccountWebviews,
  openAccountWebview,
  openAccountWebviews,
} from './serviceHost'

const statusLabel = {
  healthy: 'Estavel',
  warning: 'Atencao',
  offline: 'Offline',
} as const

const notificationLabel: Record<NotificationMode, string> = {
  native: 'Nativo',
  muted: 'Silenciado',
  mentions: 'So mencoes',
}

function nextNotificationMode(mode: NotificationMode): NotificationMode {
  if (mode === 'native') {
    return 'mentions'
  }
  if (mode === 'mentions') {
    return 'muted'
  }
  return 'native'
}

function App() {
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot>(() => loadWorkspaceSnapshot())
  const [runtimeStatus, setRuntimeStatus] = useState<'idle' | 'opening' | 'ready' | 'error'>('idle')
  const [runtimeMessage, setRuntimeMessage] = useState('Nenhuma webview real aberta nesta sessao.')
  const [openViews, setOpenViews] = useState<string[]>([])
  const [desktopStatus, setDesktopStatus] = useState<'idle' | 'tray-ready' | 'notified' | 'error'>('idle')
  const [desktopMessage, setDesktopMessage] = useState('Tray e notificacoes ainda nao inicializados.')
  const [runtimeEvents, setRuntimeEvents] = useState<string[]>([
    'Shell inicializado. Aguardando interacao do operador.',
  ])
  const restoreAttempted = useRef(false)

  function pushRuntimeEvent(message: string) {
    const timestamp = new Date().toLocaleTimeString('pt-BR')
    setRuntimeEvents((current) => [`${timestamp} • ${message}`, ...current].slice(0, 12))
  }

  useEffect(() => {
    saveWorkspaceSnapshot(workspace)
  }, [workspace])

  useEffect(() => {
    let cancelled = false

    async function syncOpenViews() {
      try {
        const views = await listAccountWebviews()
        if (!cancelled) {
          setOpenViews(views)
          setWorkspace((current) => {
            const nextLiveAccountIds = current.services
              .flatMap((service) => service.accounts)
              .filter((account) => views.includes(accountLabel(account)))
              .map((account) => account.id)

            if (JSON.stringify(nextLiveAccountIds) === JSON.stringify(current.liveAccountIds)) {
              return current
            }

            return {
              ...current,
              liveAccountIds: nextLiveAccountIds,
            }
          })
          pushRuntimeEvent(`sincronizacao concluida com ${views.length} webviews abertas`)
        }
      } catch {
        if (!cancelled) {
          setRuntimeStatus('error')
          setRuntimeMessage('falha ao sincronizar webviews ativas')
          pushRuntimeEvent('falha ao sincronizar webviews ativas')
        }
      }
    }

    void syncOpenViews()
    const intervalId = window.setInterval(() => {
      void syncOpenViews()
    }, 2_500)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const accountIndex = useMemo(() => {
    const map = new Map<string, ChatAccount>()
    for (const service of workspace.services) {
      for (const account of service.accounts) {
        map.set(account.id, account)
      }
    }
    return map
  }, [workspace.services])

  const visibleServices = useMemo(() => {
    const search = workspace.search.trim().toLowerCase()
    const services = workspace.services.filter((service) => {
      if (!search) {
        return true
      }
      return (
        service.name.toLowerCase().includes(search) ||
        service.accounts.some(
          (account) =>
            account.label.toLowerCase().includes(search) ||
            account.workspace.toLowerCase().includes(search),
        )
      )
    })

    return [...services].sort((left, right) => Number(right.pinned) - Number(left.pinned))
  }, [workspace.search, workspace.services])

  const activeService =
    workspace.services.find((service) => service.id === workspace.activeServiceId) ??
    workspace.services[0] ??
    seedWorkspace.services[0]

  const activeAccount =
    activeService.accounts.find((account) => account.id === workspace.activeAccountId) ??
    activeService.accounts[0]

  const totalUnread = useMemo(
    () => workspace.services.reduce((sum, service) => sum + service.unread, 0),
    [workspace.services],
  )

  const connectedAccounts = useMemo(
    () => workspace.services.reduce((sum, service) => sum + service.accounts.length, 0),
    [workspace.services],
  )

  useEffect(() => {
    if (restoreAttempted.current || !workspace.preferences.restoreLiveSessions) {
      return
    }
    if (openViews.length > 0 || workspace.liveAccountIds.length === 0) {
      restoreAttempted.current = true
      return
    }

    const accountsToRestore = workspace.liveAccountIds
      .map((accountId) => accountIndex.get(accountId))
      .filter((account): account is ChatAccount => !!account)

    if (accountsToRestore.length === 0) {
      restoreAttempted.current = true
      return
    }

    restoreAttempted.current = true
    setRuntimeStatus('opening')
    setRuntimeMessage(`Restaurando ${accountsToRestore.length} webviews persistidas...`)
    pushRuntimeEvent(`restauracao automatica iniciada para ${accountsToRestore.length} sessoes`)
    void openAccountWebviews(accountsToRestore)
      .then(async () => {
        const views = await listAccountWebviews()
        setOpenViews(views)
        setRuntimeStatus('ready')
        setRuntimeMessage(`${views.length} webviews restauradas a partir do ultimo workspace.`)
        pushRuntimeEvent(`${views.length} webviews restauradas a partir do ultimo workspace`)
      })
      .catch((error) => {
        setRuntimeStatus('error')
        setRuntimeMessage(
          error instanceof Error ? error.message : 'falha ao restaurar webviews persistidas',
        )
        pushRuntimeEvent('falha na restauracao automatica de sessoes')
      })
  }, [accountIndex, openViews.length, workspace.liveAccountIds, workspace.preferences.restoreLiveSessions])

  function updateWorkspace(recipe: (current: WorkspaceSnapshot) => WorkspaceSnapshot) {
    setWorkspace((current) => recipe(current))
  }

  function selectService(service: ChatService) {
    updateWorkspace((current) => ({
      ...current,
      activeServiceId: service.id,
      activeAccountId: service.accounts[0]?.id ?? current.activeAccountId,
    }))
  }

  function selectAccount(account: ChatAccount) {
    updateWorkspace((current) => ({
      ...current,
      activeAccountId: account.id,
    }))
  }

  function toggleServicePin(serviceId: string) {
    updateWorkspace((current) => ({
      ...current,
      services: current.services.map((service) =>
        service.id === serviceId ? { ...service, pinned: !service.pinned } : service,
      ),
    }))
  }

  function togglePreferences(key: keyof WorkspaceSnapshot['preferences']) {
    updateWorkspace((current) => ({
      ...current,
      preferences: {
        ...current.preferences,
        [key]: !current.preferences[key],
      },
    }))
  }

  function cycleNotifications(accountId: string) {
    updateWorkspace((current) => ({
      ...current,
      services: current.services.map((service) => ({
        ...service,
        accounts: service.accounts.map((account) =>
          account.id === accountId
            ? {
                ...account,
                notifications: nextNotificationMode(account.notifications),
              }
            : account,
        ),
      })),
    }))
  }

  function resetWorkspace() {
    setWorkspace(seedWorkspace)
  }

  function rememberOpenAccount(accountId: string, isOpen: boolean) {
    setWorkspace((current) => {
      const nextLiveAccountIds = isOpen
        ? Array.from(new Set([...current.liveAccountIds, accountId]))
        : current.liveAccountIds.filter((candidate) => candidate !== accountId)

      return {
        ...current,
        liveAccountIds: nextLiveAccountIds,
      }
    })
  }

  async function handleOpenLiveView(account: ChatAccount) {
    setRuntimeStatus('opening')
    setRuntimeMessage(`Abrindo webview real para ${account.label}...`)
    pushRuntimeEvent(`abrindo webview de ${account.label}`)
    try {
      const label = await openAccountWebview(account)
      const views = await listAccountWebviews()
      setOpenViews(views)
      rememberOpenAccount(account.id, true)
      setRuntimeStatus('ready')
      setRuntimeMessage(`Webview ${label} ativa com storage isolado para ${account.profile}.`)
      pushRuntimeEvent(`webview ${label} aberta com isolamento ${account.profile}`)
    } catch (error) {
      setRuntimeStatus('error')
      setRuntimeMessage(error instanceof Error ? error.message : 'falha ao abrir webview')
      pushRuntimeEvent(`falha ao abrir webview de ${account.label}`)
    }
  }

  async function handleCloseLiveView(account: ChatAccount) {
    try {
      await closeAccountWebview(account)
      const views = await listAccountWebviews()
      setOpenViews(views)
      rememberOpenAccount(account.id, false)
      setRuntimeStatus('idle')
      setRuntimeMessage(`Webview de ${account.label} encerrada.`)
      pushRuntimeEvent(`webview de ${account.label} encerrada`)
    } catch (error) {
      setRuntimeStatus('error')
      setRuntimeMessage(error instanceof Error ? error.message : 'falha ao fechar webview')
      pushRuntimeEvent(`falha ao fechar webview de ${account.label}`)
    }
  }

  async function handleOpenServiceViews(service: ChatService) {
    setRuntimeStatus('opening')
    setRuntimeMessage(`Abrindo ${service.accounts.length} webviews de ${service.name}...`)
    pushRuntimeEvent(`abertura em lote de ${service.accounts.length} contas de ${service.name}`)
    try {
      await openAccountWebviews(service.accounts)
      const views = await listAccountWebviews()
      setOpenViews(views)
      setWorkspace((current) => ({
        ...current,
        liveAccountIds: Array.from(
          new Set([...current.liveAccountIds, ...service.accounts.map((account) => account.id)]),
        ),
      }))
      setRuntimeStatus('ready')
      setRuntimeMessage(`${service.accounts.length} webviews de ${service.name} ativas.`)
      pushRuntimeEvent(`${service.accounts.length} webviews de ${service.name} foram abertas`)
    } catch (error) {
      setRuntimeStatus('error')
      setRuntimeMessage(error instanceof Error ? error.message : 'falha ao abrir webviews do servico')
      pushRuntimeEvent(`falha na abertura em lote de ${service.name}`)
    }
  }

  async function handleCloseServiceViews(service: ChatService) {
    try {
      await closeAccountWebviews(service.accounts)
      const views = await listAccountWebviews()
      setOpenViews(views)
      setWorkspace((current) => ({
        ...current,
        liveAccountIds: current.liveAccountIds.filter(
          (accountId) => !service.accounts.some((account) => account.id === accountId),
        ),
      }))
      setRuntimeStatus('idle')
      setRuntimeMessage(`Webviews de ${service.name} encerradas.`)
      pushRuntimeEvent(`webviews de ${service.name} encerradas em lote`)
    } catch (error) {
      setRuntimeStatus('error')
      setRuntimeMessage(error instanceof Error ? error.message : 'falha ao fechar webviews do servico')
      pushRuntimeEvent(`falha ao fechar webviews de ${service.name}`)
    }
  }

  async function handleSyncRuntime() {
    try {
      const views = await listAccountWebviews()
      setOpenViews(views)
      setRuntimeStatus(views.length > 0 ? 'ready' : 'idle')
      setRuntimeMessage(
        views.length > 0
          ? `${views.length} webviews reconciliadas manualmente.`
          : 'Nenhuma webview aberta apos reconciliacao manual.',
      )
      pushRuntimeEvent(`reconciliacao manual executada com ${views.length} webviews abertas`)
    } catch (error) {
      setRuntimeStatus('error')
      setRuntimeMessage(error instanceof Error ? error.message : 'falha ao reconciliar runtime')
      pushRuntimeEvent('falha na reconciliacao manual do runtime')
    }
  }

  async function handleCloseAllLiveViews() {
    const accountsToClose = workspace.services
      .flatMap((service) => service.accounts)
      .filter((account) => workspace.liveAccountIds.includes(account.id))

    if (accountsToClose.length === 0) {
      setRuntimeStatus('idle')
      setRuntimeMessage('Nenhuma webview persistida para encerrar.')
      pushRuntimeEvent('nenhuma webview persistida para encerrar')
      return
    }

    try {
      await closeAccountWebviews(accountsToClose)
      const views = await listAccountWebviews()
      setOpenViews(views)
      setWorkspace((current) => ({
        ...current,
        liveAccountIds: [],
      }))
      setRuntimeStatus('idle')
      setRuntimeMessage('Todas as webviews persistidas foram encerradas.')
      pushRuntimeEvent(`encerramento global concluido para ${accountsToClose.length} webviews`)
    } catch (error) {
      setRuntimeStatus('error')
      setRuntimeMessage(error instanceof Error ? error.message : 'falha ao encerrar todas as webviews')
      pushRuntimeEvent('falha ao encerrar todas as webviews persistidas')
    }
  }

  async function handleEnsureTray() {
    try {
      const trayId = await ensureTray(() => {
        setDesktopStatus('tray-ready')
        setDesktopMessage(`Pulse manual recebido pelo tray em ${new Date().toLocaleTimeString('pt-BR')}.`)
      })
      setDesktopStatus('tray-ready')
      setDesktopMessage(`Tray ${trayId} ativo para o shell do OctoChat.`)
    } catch (error) {
      setDesktopStatus('error')
      setDesktopMessage(error instanceof Error ? error.message : 'falha ao criar tray')
    }
  }

  async function handleNotification() {
    try {
      await pushDesktopNotification(
        `OctoChat • ${activeService.name}`,
        `${activeAccount.label} esta pronto para validar a sessao real.`,
      )
      setDesktopStatus('notified')
      setDesktopMessage(`Notificacao disparada para ${activeAccount.label}.`)
      pushRuntimeEvent(`notificacao nativa disparada para ${activeAccount.label}`)
    } catch (error) {
      setDesktopStatus('error')
      setDesktopMessage(error instanceof Error ? error.message : 'falha ao disparar notificacao')
      pushRuntimeEvent(`falha ao disparar notificacao para ${activeAccount.label}`)
    }
  }

  return (
    <main className={`app-shell ${workspace.preferences.compactRail ? 'compact-rail' : ''}`}>
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">OctoChat / R0</p>
          <h1>Shell multichat com contrato real de workspace e sessao.</h1>
          <p className="summary">
            O recorte agora sai do mock estatico: servicos, contas, preferencias e foco do
            operador ficam persistidos localmente. Isso reduz a lacuna entre o shell visual e o
            runtime Tauri que vai hospedar webviews isoladas por conta.
          </p>
        </div>
        <div className="hero-grid">
          <article>
            <span>Servicos fixados</span>
            <strong>{workspace.services.filter((service) => service.pinned).length}</strong>
          </article>
          <article>
            <span>Contas conectadas</span>
            <strong>{connectedAccounts}</strong>
          </article>
          <article>
            <span>Unread agregado</span>
            <strong>{totalUnread}</strong>
          </article>
        </div>
      </section>

      <section className="workspace">
        <aside className="service-rail">
          <div className="rail-header">
            <div>
              <span>Servicos</span>
              <strong>{visibleServices.length}</strong>
            </div>
            <button className="ghost-button" onClick={() => togglePreferences('compactRail')} type="button">
              {workspace.preferences.compactRail ? 'Expandir' : 'Compactar'}
            </button>
          </div>

          <label className="search-box">
            <span>Busca rapida</span>
            <input
              onChange={(event) =>
                updateWorkspace((current) => ({
                  ...current,
                  search: event.target.value,
                }))
              }
              placeholder="Slack, suporte, ops..."
              type="search"
              value={workspace.search}
            />
          </label>

          <div className="service-list">
            {visibleServices.map((service) => (
              <article
                key={service.id}
                className={`service-card ${service.id === activeService.id ? 'active' : ''}`}
              >
                <button className="service-main" onClick={() => selectService(service)} type="button">
                  <span className="service-badge" style={{ backgroundColor: service.color }}>
                    {service.icon}
                  </span>
                  <span className="service-copy">
                    <strong>{service.name}</strong>
                    <small>{statusLabel[service.status]}</small>
                  </span>
                  <span className="unread-pill">{service.unread}</span>
                </button>
                <button className="pin-toggle" onClick={() => toggleServicePin(service.id)} type="button">
                  {service.pinned ? 'Fixado' : 'Fixar'}
                </button>
                <div className="service-actions">
                  <button className="pin-toggle secondary" onClick={() => void handleOpenServiceViews(service)} type="button">
                    Abrir tudo
                  </button>
                  <button className="pin-toggle secondary" onClick={() => void handleCloseServiceViews(service)} type="button">
                    Fechar tudo
                  </button>
                </div>
              </article>
            ))}
          </div>
        </aside>

        <section className="stage">
          <header className="stage-header">
            <div>
              <p className="eyebrow">Servico ativo</p>
              <h2>{activeService.name}</h2>
            </div>
            <div className={`health health-${activeService.status}`}>{statusLabel[activeService.status]}</div>
          </header>

          <div className="account-strip">
            {activeService.accounts.map((account) => (
              <button
                key={account.id}
                className={`account-chip ${account.id === activeAccount.id ? 'active' : ''}`}
                onClick={() => selectAccount(account)}
                type="button"
              >
                <strong>{account.label}</strong>
                <span>{account.workspace}</span>
              </button>
            ))}
          </div>

          <article className="webview-stage">
            <div className="browser-bar">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
              <p>{activeAccount.profile}</p>
            </div>
            <div className="webview-body">
              <div className="mock-pane">
                <p className="eyebrow">Webview slot</p>
                <h3>{activeAccount.label}</h3>
                <p>
                  A webview final sera anexada a este slot com store/cookies segregados pelo
                  identificador <code>{activeAccount.profile}</code>.
                </p>
                <div className="slot-actions">
                  <button className="preference-toggle" onClick={() => void handleOpenLiveView(activeAccount)} type="button">
                    Abrir webview real
                  </button>
                  <button className="preference-toggle" onClick={() => void handleCloseLiveView(activeAccount)} type="button">
                    Fechar webview
                  </button>
                </div>
                <dl className="slot-contract">
                  <div>
                    <dt>URL alvo</dt>
                    <dd>{activeAccount.serviceUrl}</dd>
                  </div>
                  <div>
                    <dt>Workspace</dt>
                    <dd>{activeAccount.workspace}</dd>
                  </div>
                  <div>
                    <dt>Politica</dt>
                    <dd>isolamento por conta + reload controlado</dd>
                  </div>
                </dl>
              </div>
              {workspace.preferences.showTelemetry ? (
                <div className="telemetry">
                  <div>
                    <span>Saude da sessao</span>
                    <strong>{statusLabel[activeAccount.health]}</strong>
                  </div>
                  <div>
                    <span>Notificacoes</span>
                    <strong>{notificationLabel[activeAccount.notifications]}</strong>
                  </div>
                  <div>
                    <span>Ultimo heartbeat</span>
                    <strong>{activeAccount.lastSync}</strong>
                  </div>
                </div>
              ) : null}
            </div>
          </article>
        </section>

        <aside className="inspector">
          <section className="inspector-card">
            <p className="eyebrow">Operacao</p>
            <div className="preferences-grid">
              <button className="preference-toggle" onClick={() => togglePreferences('showTelemetry')} type="button">
                {workspace.preferences.showTelemetry ? 'Ocultar telemetria' : 'Mostrar telemetria'}
              </button>
              <button className="preference-toggle" onClick={() => togglePreferences('focusMode')} type="button">
                {workspace.preferences.focusMode ? 'Desligar focus mode' : 'Ligar focus mode'}
              </button>
              <button
                className="preference-toggle"
                onClick={() => togglePreferences('restoreLiveSessions')}
                type="button"
              >
                {workspace.preferences.restoreLiveSessions ? 'Nao restaurar sessoes' : 'Restaurar sessoes'}
              </button>
              <button className="preference-toggle danger" onClick={resetWorkspace} type="button">
                Resetar workspace
              </button>
            </div>
          </section>

          <section className="inspector-card">
            <p className="eyebrow">Sessao ativa</p>
            <ul className="detail-list">
              <li>
                <span>Profile</span>
                <strong>{activeAccount.profile}</strong>
              </li>
              <li>
                <span>Storage bucket</span>
                <strong>{activeAccount.id}</strong>
              </li>
              <li>
                <span>Focus mode</span>
                <strong>{workspace.preferences.focusMode ? 'Ativo' : 'Normal'}</strong>
              </li>
              <li>
                <span>Restore startup</span>
                <strong>{workspace.preferences.restoreLiveSessions ? 'Ativo' : 'Desligado'}</strong>
              </li>
            </ul>
            <button className="preference-toggle" onClick={() => cycleNotifications(activeAccount.id)} type="button">
              Alternar notificacoes
            </button>
          </section>

          <section className="inspector-card">
            <p className="eyebrow">Runtime Tauri</p>
            <div className="preferences-grid">
              <button className="preference-toggle" onClick={() => void handleSyncRuntime()} type="button">
                Sincronizar runtime
              </button>
              <button className="preference-toggle" onClick={() => void handleCloseAllLiveViews()} type="button">
                Fechar todas
              </button>
            </div>
            <ul className="detail-list">
              <li>
                <span>Status</span>
                <strong>{runtimeStatus}</strong>
              </li>
              <li>
                <span>Webviews abertas</span>
                <strong>{openViews.length}</strong>
              </li>
              <li>
                <span>Sessoes persistidas</span>
                <strong>{workspace.liveAccountIds.length}</strong>
              </li>
              <li>
                <span>Mensagem</span>
                <strong>{runtimeMessage}</strong>
              </li>
            </ul>
            <div className="event-log">
              {runtimeEvents.map((event) => (
                <p key={event}>{event}</p>
              ))}
            </div>
          </section>

          <section className="inspector-card">
            <p className="eyebrow">Desktop Shell</p>
            <div className="preferences-grid">
              <button className="preference-toggle" onClick={() => void handleEnsureTray()} type="button">
                Inicializar tray
              </button>
              <button className="preference-toggle" onClick={() => void handleNotification()} type="button">
                Enviar notificacao
              </button>
            </div>
            <ul className="detail-list">
              <li>
                <span>Status</span>
                <strong>{desktopStatus}</strong>
              </li>
              <li>
                <span>Mensagem</span>
                <strong>{desktopMessage}</strong>
              </li>
            </ul>
          </section>

          <section className="inspector-card accent">
            <p className="eyebrow">Snapshot local</p>
            <pre>{JSON.stringify(workspace, null, 2)}</pre>
          </section>
        </aside>
      </section>
    </main>
  )
}

export default App

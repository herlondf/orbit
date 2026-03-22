import {
  app,
  BrowserWindow,
  WebContentsView,
  ipcMain,
  session,
  shell,
  Tray,
  Menu,
  nativeImage,
  Notification,
} from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'

// ─── constants ────────────────────────────────────────────────────────────────

const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'

const IS_DEV = process.env.NODE_ENV === 'development' || !!process.env.ELECTRON_RENDERER_URL

// ─── state ────────────────────────────────────────────────────────────────────

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null

// label → WebContentsView
const views = new Map<string, WebContentsView>()
// webContents.id → label (for IPC routing from service preloads)
const wcIdToLabel = new Map<number, string>()

// Global service IPC listeners (registered once at startup, not per-view)
function setupServiceIpcListeners(): void {
  ipcMain.on('service:badge', (event, count: number) => {
    const label = wcIdToLabel.get(event.sender.id)
    if (label) mainWindow?.webContents.send('webview:badge', { label, count })
  })

  ipcMain.on('service:notify', (event, data: { title: string; body: string }) => {
    const label = wcIdToLabel.get(event.sender.id)
    if (!label) return
    mainWindow?.webContents.send('webview:notify', { label, ...data })
    if (Notification.isSupported()) new Notification({ title: data.title, body: data.body }).show()
  })
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function getPreloadPath(name: string): string {
  // electron-vite puts preloads at out/preload/<name>.js
  return join(__dirname, `../../preload/${name}.js`)
}

// ─── main window ─────────────────────────────────────────────────────────────

function createMainWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 900,
    minHeight: 600,
    title: 'OctoChat',
    backgroundColor: '#1e1e2e',
    webPreferences: {
      preload: getPreloadPath('index'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  })

  if (IS_DEV && process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(join(__dirname, '../../renderer/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ─── tray ────────────────────────────────────────────────────────────────────

function setupTray(): void {
  const icoPath = join(__dirname, '../../../resources/icon.ico')
  const pngPath = join(__dirname, '../../../resources/icon.png')
  const iconPath = existsSync(icoPath) ? icoPath : pngPath

  const icon = existsSync(iconPath)
    ? nativeImage.createFromPath(iconPath)
    : nativeImage.createEmpty()

  tray = new Tray(icon)
  tray.setToolTip('OctoChat')

  const menu = Menu.buildFromTemplate([
    {
      label: 'Mostrar OctoChat',
      click: () => {
        mainWindow?.show()
        mainWindow?.focus()
      },
    },
    { type: 'separator' },
    { label: 'Fechar', click: () => app.quit() },
  ])

  tray.setContextMenu(menu)
  tray.on('click', () => {
    mainWindow?.show()
    mainWindow?.focus()
  })
}

// ─── IPC: webview lifecycle ───────────────────────────────────────────────────

ipcMain.handle('webview:create', async (_, args: {
  label: string
  url: string
  accountId: string
  x: number
  y: number
  width: number
  height: number
}) => {
  if (!mainWindow) return
  if (views.has(args.label)) return

  const { label, url, accountId, x, y, width, height } = args

  const ses = session.fromPartition(`persist:${accountId}`)

  const view = new WebContentsView({
    webPreferences: {
      session: ses,
      preload: getPreloadPath('service'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  view.webContents.setUserAgent(USER_AGENT)

  // Hidden until explicitly shown
  view.setVisible(false)

  // WebContentsView.setBounds takes logical pixels (DIP) — same as CSS getBoundingClientRect()
  view.setBounds({ x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) })

  // ── New window handling ─────────────────────────────────────────────────────
  view.webContents.setWindowOpenHandler(({ url: newUrl }) => {
    const popup = new BrowserWindow({
      width: 960,
      height: 720,
      title: 'OctoChat – Login',
      parent: mainWindow ?? undefined,
      webPreferences: {
        session: ses, // same session = shared cookies → login persists
        contextIsolation: true,
        nodeIntegration: false,
      },
    })
    popup.loadURL(newUrl)
    popup.webContents.setUserAgent(USER_AGENT)

    // When popup closes, reload the service so it picks up the new session
    popup.on('closed', () => {
      if (!view.webContents.isDestroyed()) view.webContents.reload()
    })

    return { action: 'deny' }
  })

  // ── Badge counting via page title ────────────────────────────────────────────
  view.webContents.on('page-title-updated', (_, title) => {
    const match = title.match(/\((\d+)\)/)
    const count = match ? parseInt(match[1]) : 0
    mainWindow?.webContents.send('webview:badge', { label, count })
  })

  mainWindow.contentView.addChildView(view)
  views.set(label, view)
  wcIdToLabel.set(view.webContents.id, label)

  // Load URL non-blocking — renderer will call webview:show when ready
  view.webContents.loadURL(url).catch(() => {/* network errors are fine */})
})

ipcMain.handle('webview:show', (_, { label }: { label: string }) => {
  views.get(label)?.setVisible(true)
})

ipcMain.handle('webview:hide', (_, { label }: { label: string }) => {
  views.get(label)?.setVisible(false)
})

ipcMain.handle('webview:set-bounds', (_, args: {
  label: string; x: number; y: number; width: number; height: number
}) => {
  const view = views.get(args.label)
  if (!view) return
  view.setBounds({
    x: Math.round(args.x),
    y: Math.round(args.y),
    width: Math.round(args.width),
    height: Math.round(args.height),
  })
})

ipcMain.handle('webview:close', (_, { label }: { label: string }) => {
  const view = views.get(label)
  if (!view) return
  mainWindow?.contentView.removeChildView(view)
  wcIdToLabel.delete(view.webContents.id)
  views.delete(label)
  view.webContents.close()
})

ipcMain.handle('webview:navigate', (_, { label, url }: { label: string; url: string }) => {
  views.get(label)?.webContents.loadURL(url)
})

ipcMain.handle('webview:devtools', (_, { label }: { label: string }) => {
  views.get(label)?.webContents.openDevTools()
})

// ─── IPC: shell utilities ─────────────────────────────────────────────────────

ipcMain.handle('shell:open-external', (_, { url }: { url: string }) => {
  shell.openExternal(url)
})

ipcMain.handle('shell:notification', (_, { title, body }: { title: string; body: string }) => {
  if (Notification.isSupported()) {
    new Notification({ title, body }).show()
  }
})

ipcMain.handle('shell:tray-ready', () => 'octochat-tray')

// ─── app lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  setupServiceIpcListeners()
  createMainWindow()
  setupTray()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
})

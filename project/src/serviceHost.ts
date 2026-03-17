import { invoke } from '@tauri-apps/api/core'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'
import { getCurrentWindow } from '@tauri-apps/api/window'
import type { ChatAccount } from './contracts'

type SessionContract = {
  accountId: string
  profile: string
  serviceUrl: string
  storagePartition: string
}

function sanitizeLabel(value: string): string {
  return value.replace(/[^a-zA-Z0-9\-/:_]/g, '_')
}

function webviewLabel(account: ChatAccount): string {
  return sanitizeLabel(`chat:${account.id}`)
}

export function accountLabel(account: ChatAccount): string {
  return webviewLabel(account)
}

export async function openAccountWebview(account: ChatAccount): Promise<string> {
  const existing = await WebviewWindow.getByLabel(webviewLabel(account))
  if (existing) {
    await existing.show()
    await existing.setFocus()
    return existing.label
  }

  const contract = await invoke<SessionContract>('build_session_contract', {
    accountId: account.id,
    profile: account.profile,
    serviceUrl: account.serviceUrl,
  })

  const parent = getCurrentWindow()
  const view = new WebviewWindow(webviewLabel(account), {
    title: `${account.label} • OctoChat`,
    url: account.serviceUrl,
    width: 1280,
    height: 900,
    minWidth: 980,
    minHeight: 720,
    visible: true,
    focus: true,
    center: true,
    parent,
    dataDirectory: sanitizeLabel(contract.storagePartition),
    incognito: false,
  })

  await new Promise<void>((resolve, reject) => {
    let settled = false
    void view.once('tauri://created', () => {
      settled = true
      resolve()
    })
    void view.once('tauri://error', (event) => {
      settled = true
      reject(new Error(String(event.payload)))
    })
    window.setTimeout(() => {
      if (!settled) {
        reject(new Error('timeout creating webview'))
      }
    }, 10_000)
  })

  return view.label
}

export async function closeAccountWebview(account: ChatAccount): Promise<void> {
  const existing = await WebviewWindow.getByLabel(webviewLabel(account))
  if (existing) {
    await existing.close()
  }
}

export async function openAccountWebviews(accounts: ChatAccount[]): Promise<string[]> {
  const labels: string[] = []
  for (const account of accounts) {
    labels.push(await openAccountWebview(account))
  }
  return labels
}

export async function closeAccountWebviews(accounts: ChatAccount[]): Promise<void> {
  for (const account of accounts) {
    await closeAccountWebview(account)
  }
}

export async function listAccountWebviews(): Promise<string[]> {
  const windows = await WebviewWindow.getAll()
  return windows.map((window) => window.label).filter((label) => label.startsWith('chat:'))
}

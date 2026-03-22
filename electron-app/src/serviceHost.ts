import { invoke } from './ipc'
import type { ChatAccount } from './contracts'

function sanitizeLabel(value: string): string {
  return value.replace(/[^a-zA-Z0-9\-/:_]/g, '_')
}

export function accountLabel(account: ChatAccount): string {
  return sanitizeLabel(`chat:${account.id}`)
}

export async function createEmbeddedWebview(
  account: ChatAccount,
  x: number,
  y: number,
  width: number,
  height: number,
): Promise<void> {
  await invoke('webview:create', {
    label: accountLabel(account),
    url: account.serviceUrl,
    accountId: account.id,
    x, y, width, height,
  })
}

export async function showWebview(label: string): Promise<void> {
  await invoke('webview:show', { label })
}

export async function hideWebview(label: string): Promise<void> {
  await invoke('webview:hide', { label })
}

export async function setWebviewBounds(
  label: string, x: number, y: number, width: number, height: number,
): Promise<void> {
  await invoke('webview:set-bounds', { label, x, y, width, height })
}

export async function closeWebview(label: string): Promise<void> {
  await invoke('webview:close', { label })
}

export async function navigateWebview(label: string, url: string): Promise<void> {
  await invoke('webview:navigate', { label, url })
}

export async function openExternal(url: string): Promise<void> {
  await invoke('shell:open-external', { url })
}

export async function openWebviewDevtools(label: string): Promise<void> {
  await invoke('webview:devtools', { label })
}

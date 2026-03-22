import { invoke } from '@tauri-apps/api/core'
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
  await invoke('create_embedded_webview', {
    label: accountLabel(account),
    url: account.serviceUrl,
    accountId: account.id,
    x,
    y,
    width,
    height,
  })
}

export async function showWebview(label: string): Promise<void> {
  await invoke('show_webview', { label })
}

export async function hideWebview(label: string): Promise<void> {
  await invoke('hide_webview', { label })
}

export async function setWebviewBounds(
  label: string,
  x: number,
  y: number,
  width: number,
  height: number,
): Promise<void> {
  await invoke('set_webview_bounds', { label, x, y, width, height })
}

export async function closeWebview(label: string): Promise<void> {
  await invoke('close_webview', { label })
}

export async function navigateWebview(label: string, url: string): Promise<void> {
  await invoke('navigate_webview', { label, url })
}

export async function openExternal(url: string): Promise<void> {
  await invoke('open_external', { url })
}

export async function openWebviewDevtools(label: string): Promise<void> {
  await invoke('open_webview_devtools', { label })
}

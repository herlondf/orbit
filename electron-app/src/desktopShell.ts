import { invoke } from './ipc'

// Tray is set up in the Electron main process.
// This function signals readiness and returns a stable ID.
export async function ensureTray(_onPulse: () => void): Promise<string> {
  return invoke<string>('shell:tray-ready')
}

// Show an OS notification via the main process (avoids renderer permission issues).
export async function pushDesktopNotification(title: string, body: string): Promise<string> {
  await invoke('shell:notification', { title, body })
  return 'notification-dispatched'
}

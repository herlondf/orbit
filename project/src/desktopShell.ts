import { defaultWindowIcon } from '@tauri-apps/api/app'
import { Menu } from '@tauri-apps/api/menu'
import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification'
import { TrayIcon } from '@tauri-apps/api/tray'
import { getCurrentWindow } from '@tauri-apps/api/window'

let tray: TrayIcon | null = null

export async function ensureTray(onPulse: () => void): Promise<string> {
  if (tray) {
    return tray.id
  }

  const showItem = {
    id: 'show-main',
    text: 'Mostrar OctoChat',
    action: () => {
      void getCurrentWindow().show()
      void getCurrentWindow().setFocus()
    },
  }

  const pulseItem = {
    id: 'pulse-state',
    text: 'Pulse de atividade',
    action: () => onPulse(),
  }

  const quitItem = {
    id: 'quit-app',
    text: 'Fechar shell',
    action: () => {
      void getCurrentWindow().close()
    },
  }

  const menu = await Menu.new({ items: [showItem, pulseItem, quitItem] })
  const icon = await defaultWindowIcon()

  tray = await TrayIcon.new({
    id: 'octochat-shell',
    tooltip: 'OctoChat shell desktop',
    menu,
    icon: icon ?? undefined,
    showMenuOnLeftClick: true,
    action: (event) => {
      if (event.type === 'Click' && event.button === 'Left' && event.buttonState === 'Up') {
        void getCurrentWindow().show()
        void getCurrentWindow().setFocus()
      }
    },
  })

  return tray.id
}

export async function pushDesktopNotification(title: string, body: string): Promise<string> {
  let permissionGranted = await isPermissionGranted()
  if (!permissionGranted) {
    const permission = await requestPermission()
    permissionGranted = permission === 'granted'
  }

  if (!permissionGranted) {
    throw new Error('permissao de notificacao negada')
  }

  sendNotification({ title, body })
  return 'notification-dispatched'
}

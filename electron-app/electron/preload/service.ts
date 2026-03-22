// Service preload — runs inside each WebContentsView (service page).
// Has access to ipcRenderer via Node.js (preload privilege).
// contextIsolation: true keeps this isolated from page scripts.

const { ipcRenderer } = require('electron') as typeof import('electron')

// ── Badge counting via page title ────────────────────────────────────────────
// Pattern: "(3) WhatsApp" or "Slack (2) #channel"
// MutationObserver fires whenever the title element changes.
function reportBadge() {
  const match = document.title.match(/\((\d+)\)/)
  const count = match ? parseInt(match[1], 10) : 0
  ipcRenderer.send('service:badge', count)
}

const titleObserver = new MutationObserver(reportBadge)

document.addEventListener('DOMContentLoaded', () => {
  const titleEl = document.querySelector('title')
  if (titleEl) {
    titleObserver.observe(titleEl, { childList: true, characterData: true, subtree: true })
  } else {
    titleObserver.observe(document.head, { childList: true, subtree: true })
  }
  reportBadge()
})

// ── Notification interception ────────────────────────────────────────────────
// Override window.Notification so service notifications become shell toasts.
const OriginalNotification = window.Notification

function OctoNotification(title: string, options?: NotificationOptions): Notification {
  ipcRenderer.send('service:notify', { title, body: options?.body ?? '' })
  return new OriginalNotification(title, options)
}

OctoNotification.permission = OriginalNotification.permission
OctoNotification.requestPermission =
  OriginalNotification.requestPermission.bind(OriginalNotification)

;(window as unknown as Record<string, unknown>).Notification = OctoNotification

export {}

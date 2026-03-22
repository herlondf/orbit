import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'

// Expose a safe, typed bridge to the React renderer.
// The renderer uses window.electronAPI — no direct Node.js access.

type AnyFn = (payload: unknown) => void

contextBridge.exposeInMainWorld('electronAPI', {
  invoke: (channel: string, payload?: unknown): Promise<unknown> =>
    ipcRenderer.invoke(channel, payload),

  on: (channel: string, callback: AnyFn): (() => void) => {
    const handler = (_: IpcRendererEvent, payload: unknown) => callback(payload)
    ipcRenderer.on(channel, handler)
    return () => ipcRenderer.removeListener(channel, handler)
  },
})

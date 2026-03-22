// Typed wrapper around window.electronAPI (exposed by electron/preload/index.ts).
// Use these helpers everywhere instead of calling window.electronAPI directly.

declare global {
  interface Window {
    electronAPI: {
      invoke(channel: string, payload?: unknown): Promise<unknown>
      on(channel: string, callback: (payload: unknown) => void): () => void
    }
  }
}

export function invoke<T = void>(channel: string, payload?: unknown): Promise<T> {
  return window.electronAPI.invoke(channel, payload) as Promise<T>
}

/** Subscribes to a main-process event. Returns an unlisten function. */
export function on<T>(channel: string, callback: (payload: T) => void): () => void {
  return window.electronAPI.on(channel, (p) => callback(p as T))
}

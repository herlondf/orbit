"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  invoke: (channel, payload) => electron.ipcRenderer.invoke(channel, payload),
  on: (channel, callback) => {
    const handler = (_, payload) => callback(payload);
    electron.ipcRenderer.on(channel, handler);
    return () => electron.ipcRenderer.removeListener(channel, handler);
  }
});

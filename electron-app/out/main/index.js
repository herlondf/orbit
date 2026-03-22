"use strict";
const electron = require("electron");
const path = require("path");
const fs = require("fs");
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
const IS_DEV = process.env.NODE_ENV === "development" || !!process.env.ELECTRON_RENDERER_URL;
let mainWindow = null;
let tray = null;
const views = /* @__PURE__ */ new Map();
const wcIdToLabel = /* @__PURE__ */ new Map();
function setupServiceIpcListeners() {
  electron.ipcMain.on("service:badge", (event, count) => {
    const label = wcIdToLabel.get(event.sender.id);
    if (label) mainWindow?.webContents.send("webview:badge", { label, count });
  });
  electron.ipcMain.on("service:notify", (event, data) => {
    const label = wcIdToLabel.get(event.sender.id);
    if (!label) return;
    mainWindow?.webContents.send("webview:notify", { label, ...data });
    if (electron.Notification.isSupported()) new electron.Notification({ title: data.title, body: data.body }).show();
  });
}
function getPreloadPath(name) {
  return path.join(__dirname, `../../preload/${name}.js`);
}
function createMainWindow() {
  mainWindow = new electron.BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 900,
    minHeight: 600,
    title: "OctoChat",
    backgroundColor: "#1e1e2e",
    webPreferences: {
      preload: getPreloadPath("index"),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true
    }
  });
  if (IS_DEV && process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(__dirname, "../../renderer/index.html"));
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}
function setupTray() {
  const icoPath = path.join(__dirname, "../../../resources/icon.ico");
  const pngPath = path.join(__dirname, "../../../resources/icon.png");
  const iconPath = fs.existsSync(icoPath) ? icoPath : pngPath;
  const icon = fs.existsSync(iconPath) ? electron.nativeImage.createFromPath(iconPath) : electron.nativeImage.createEmpty();
  tray = new electron.Tray(icon);
  tray.setToolTip("OctoChat");
  const menu = electron.Menu.buildFromTemplate([
    {
      label: "Mostrar OctoChat",
      click: () => {
        mainWindow?.show();
        mainWindow?.focus();
      }
    },
    { type: "separator" },
    { label: "Fechar", click: () => electron.app.quit() }
  ]);
  tray.setContextMenu(menu);
  tray.on("click", () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}
electron.ipcMain.handle("webview:create", async (_, args) => {
  if (!mainWindow) return;
  if (views.has(args.label)) return;
  const { label, url, accountId, x, y, width, height } = args;
  const ses = electron.session.fromPartition(`persist:${accountId}`);
  const view = new electron.WebContentsView({
    webPreferences: {
      session: ses,
      preload: getPreloadPath("service"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  view.webContents.setUserAgent(USER_AGENT);
  view.setVisible(false);
  view.setBounds({ x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) });
  view.webContents.setWindowOpenHandler(({ url: newUrl }) => {
    const popup = new electron.BrowserWindow({
      width: 960,
      height: 720,
      title: "OctoChat – Login",
      parent: mainWindow ?? void 0,
      webPreferences: {
        session: ses,
        // same session = shared cookies → login persists
        contextIsolation: true,
        nodeIntegration: false
      }
    });
    popup.loadURL(newUrl);
    popup.webContents.setUserAgent(USER_AGENT);
    popup.on("closed", () => {
      if (!view.webContents.isDestroyed()) view.webContents.reload();
    });
    return { action: "deny" };
  });
  view.webContents.on("page-title-updated", (_2, title) => {
    const match = title.match(/\((\d+)\)/);
    const count = match ? parseInt(match[1]) : 0;
    mainWindow?.webContents.send("webview:badge", { label, count });
  });
  mainWindow.contentView.addChildView(view);
  views.set(label, view);
  wcIdToLabel.set(view.webContents.id, label);
  view.webContents.loadURL(url).catch(() => {
  });
});
electron.ipcMain.handle("webview:show", (_, { label }) => {
  views.get(label)?.setVisible(true);
});
electron.ipcMain.handle("webview:hide", (_, { label }) => {
  views.get(label)?.setVisible(false);
});
electron.ipcMain.handle("webview:set-bounds", (_, args) => {
  const view = views.get(args.label);
  if (!view) return;
  view.setBounds({
    x: Math.round(args.x),
    y: Math.round(args.y),
    width: Math.round(args.width),
    height: Math.round(args.height)
  });
});
electron.ipcMain.handle("webview:close", (_, { label }) => {
  const view = views.get(label);
  if (!view) return;
  mainWindow?.contentView.removeChildView(view);
  wcIdToLabel.delete(view.webContents.id);
  views.delete(label);
  view.webContents.close();
});
electron.ipcMain.handle("webview:navigate", (_, { label, url }) => {
  views.get(label)?.webContents.loadURL(url);
});
electron.ipcMain.handle("webview:devtools", (_, { label }) => {
  views.get(label)?.webContents.openDevTools();
});
electron.ipcMain.handle("shell:open-external", (_, { url }) => {
  electron.shell.openExternal(url);
});
electron.ipcMain.handle("shell:notification", (_, { title, body }) => {
  if (electron.Notification.isSupported()) {
    new electron.Notification({ title, body }).show();
  }
});
electron.ipcMain.handle("shell:tray-ready", () => "octochat-tray");
electron.app.whenReady().then(() => {
  setupServiceIpcListeners();
  createMainWindow();
  setupTray();
});
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") electron.app.quit();
});
electron.app.on("activate", () => {
  if (electron.BrowserWindow.getAllWindows().length === 0) createMainWindow();
});

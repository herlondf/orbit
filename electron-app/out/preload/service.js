"use strict";
const { ipcRenderer } = require("electron");
function reportBadge() {
  const match = document.title.match(/\((\d+)\)/);
  const count = match ? parseInt(match[1], 10) : 0;
  ipcRenderer.send("service:badge", count);
}
const titleObserver = new MutationObserver(reportBadge);
document.addEventListener("DOMContentLoaded", () => {
  const titleEl = document.querySelector("title");
  if (titleEl) {
    titleObserver.observe(titleEl, { childList: true, characterData: true, subtree: true });
  } else {
    titleObserver.observe(document.head, { childList: true, subtree: true });
  }
  reportBadge();
});
const OriginalNotification = window.Notification;
function OctoNotification(title, options) {
  ipcRenderer.send("service:notify", { title, body: options?.body ?? "" });
  return new OriginalNotification(title, options);
}
OctoNotification.permission = OriginalNotification.permission;
OctoNotification.requestPermission = OriginalNotification.requestPermission.bind(OriginalNotification);
window.Notification = OctoNotification;

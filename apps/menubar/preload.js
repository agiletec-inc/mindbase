const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("SettingsAPI", {
  get: () => ipcRenderer.invoke("settings:get"),
  save: (payload) => ipcRenderer.invoke("settings:save", payload),
  onUpdate: (callback) => {
    ipcRenderer.on("settings:updated", (_event, data) => callback(data));
  },
});

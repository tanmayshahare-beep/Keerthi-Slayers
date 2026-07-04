const { contextBridge, ipcRenderer } = require("electron");

// contextIsolation is on by default (no webPreferences overrides in
// main.js besides this preload) - the renderer can't reach ipcRenderer or
// Node directly, so this is the one narrow bridge it gets: exporting the
// current page to a PDF the user picks a save location for.
contextBridge.exposeInMainWorld("electronAPI", {
  exportPdf: (options) => ipcRenderer.invoke("export-pdf", options),
});

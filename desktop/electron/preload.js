const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('bridge', {
  getProxyStatus: () => ipcRenderer.invoke('get-proxy-status'),
  apiFetch: (method, url, body) =>
    ipcRenderer.invoke('api-fetch', method, url, body),
})

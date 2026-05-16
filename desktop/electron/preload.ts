import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('bridge', {
  getProxyStatus: () => ipcRenderer.invoke('get-proxy-status'),
  apiFetch: (method: string, url: string, body?: unknown) =>
    ipcRenderer.invoke('api-fetch', method, url, body),
})

/// <reference types="vite/client" />

interface Bridge {
  getProxyStatus: () => Promise<any>
  apiFetch: (method: string, url: string, body?: unknown) => Promise<any>
}

interface Window {
  bridge?: Bridge
}

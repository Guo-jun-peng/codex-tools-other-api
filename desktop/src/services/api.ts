const API_BASE = '/admin/api'

async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  return resp.json()
}

export const api = {
  // Status
  getStatus: () => fetchApi<any>('/status'),

  // Models
  getModels: () => fetchApi<{ models: any[] }>('/models'),
  addModel: (data: any) => fetchApi<any>('/models', { method: 'POST', body: JSON.stringify(data) }),
  updateModel: (alias: string, data: any) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteModel: (alias: string) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}`, { method: 'DELETE' }),
  testModel: (alias: string, data?: any) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}/test`, { method: 'POST', body: JSON.stringify(data || {}) }),

  // Settings
  getSettings: () => fetchApi<any>('/settings'),
  updateSettings: (data: any) =>
    fetchApi<any>('/settings', { method: 'PUT', body: JSON.stringify(data) }),

  // Logs
  getLogs: (limit = 100) => fetchApi<{ logs: any[] }>(`/logs?limit=${limit}`),
  clearLogs: () => fetchApi<any>('/logs/clear', { method: 'POST' }),

  // Codex config
  getCodexStatus: () => fetchApi<any>('/codex/status'),
  applyCodexConfig: (model: string, port: number) =>
    fetchApi<any>('/codex/apply', { method: 'POST', body: JSON.stringify({ model, port }) }),
  restoreCodexConfig: () =>
    fetchApi<any>('/codex/restore', { method: 'POST' }),

  // Tools
  getTools: () => fetchApi<any>('/tools'),
  updateTools: (data: any) =>
    fetchApi<any>('/tools', { method: 'PUT', body: JSON.stringify(data) }),

  // Import/Export
  exportConfig: () => fetchApi<any>('/config/export'),
  importConfig: (yaml: string) =>
    fetchApi<any>('/config/import', { method: 'POST', body: JSON.stringify({ yaml }) }),

  shutdown: () => fetchApi<any>('/shutdown', { method: 'POST' }),
}

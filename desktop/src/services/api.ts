const API_BASE = '/admin/api'

async function fetchApi<T>(url: string, options?: RequestInit): Promise<T & { _error?: string }> {
  try {
    const resp = await fetch(`${API_BASE}${url}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
    const data = await resp.json()
    if (!resp.ok) {
      return { ...data, _error: data?.error?.message || data?.error || `HTTP ${resp.status}` }
    }
    return data
  } catch (err: any) {
    return { _error: err.message || '网络连接失败，请检查代理是否运行' } as any
  }
}

export const api = {
  getStatus: () => fetchApi<any>('/status'),

  getAdapters: () => fetchApi<{ adapters: { name: string; base_url: string; api_key_env: string }[] }>('/adapters'),
  getModels: () => fetchApi<{ models: any[] }>('/models'),
  addModel: (data: any) => fetchApi<any>('/models', { method: 'POST', body: JSON.stringify(data) }),
  updateModel: (alias: string, data: any) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteModel: (alias: string) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}`, { method: 'DELETE' }),
  toggleModel: (alias: string) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}/toggle`, { method: 'PUT' }),
  testModel: (alias: string, data?: any) =>
    fetchApi<any>(`/models/${encodeURIComponent(alias)}/test`, { method: 'POST', body: JSON.stringify(data || {}) }),

  getSettings: () => fetchApi<any>('/settings'),
  updateSettings: (data: any) =>
    fetchApi<any>('/settings', { method: 'PUT', body: JSON.stringify(data) }),

  getLogs: (limit = 100) => fetchApi<{ logs: any[] }>(`/logs?limit=${limit}`),
  clearLogs: () => fetchApi<any>('/logs/clear', { method: 'POST' }),

  getCodexStatus: () => fetchApi<any>('/codex/status'),
  applyCodexConfig: (model: string, port: number) =>
    fetchApi<any>('/codex/apply', { method: 'POST', body: JSON.stringify({ model, port }) }),
  restoreCodexConfig: () =>
    fetchApi<any>('/codex/restore', { method: 'POST' }),

  getTools: () => fetchApi<any>('/tools'),
  updateTools: (data: any) =>
    fetchApi<any>('/tools', { method: 'PUT', body: JSON.stringify(data) }),

  exportConfig: () => fetchApi<any>('/config/export'),
  importConfig: (yaml: string) =>
    fetchApi<any>('/config/import', { method: 'POST', body: JSON.stringify({ yaml }) }),

  shutdown: () => fetchApi<any>('/shutdown', { method: 'POST' }),
}

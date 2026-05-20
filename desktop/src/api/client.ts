const API_BASE = '/admin/api'

export async function fetchApi<T>(url: string, options?: RequestInit): Promise<T & { _error?: string }> {
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

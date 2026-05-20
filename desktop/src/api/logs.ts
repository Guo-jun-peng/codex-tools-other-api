import { fetchApi } from './client'
import type { RequestLogEntry } from '../types/log'

export const logsApi = {
  getLogs: (limit = 100) =>
    fetchApi<{ logs: RequestLogEntry[] }>(`/logs?limit=${limit}`),

  clearLogs: () =>
    fetchApi<{ status: string }>('/logs/clear', { method: 'POST' }),
}

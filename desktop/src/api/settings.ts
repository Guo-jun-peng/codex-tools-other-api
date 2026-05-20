import { fetchApi } from './client'
import type { ServerSettings, CodexConfigStatus, ToolStatus } from '../types/settings'

export const settingsApi = {
  getSettings: () =>
    fetchApi<ServerSettings>('/settings'),

  updateSettings: (data: Record<string, unknown>) =>
    fetchApi<{ status: string; message: string }>('/settings', {
      method: 'PUT', body: JSON.stringify(data),
    }),

  getCodexStatus: () =>
    fetchApi<CodexConfigStatus>('/codex/status'),

  applyCodexConfig: (model: string, port: number) =>
    fetchApi<{ status: string; message: string }>('/codex/apply', {
      method: 'POST', body: JSON.stringify({ model, port }),
    }),

  restoreCodexConfig: () =>
    fetchApi<{ status: string; message: string }>('/codex/restore', {
      method: 'POST',
    }),

  getTools: () =>
    fetchApi<{ tools: ToolStatus }>('/tools'),

  updateTools: (data: Record<string, unknown>) =>
    fetchApi<{ status: string }>('/tools', {
      method: 'PUT', body: JSON.stringify(data),
    }),

  exportConfig: () =>
    fetchApi<{ yaml: string; config_path: string }>('/config/export'),

  importConfig: (yaml: string) =>
    fetchApi<{ status: string }>('/config/import', {
      method: 'POST', body: JSON.stringify({ yaml }),
    }),

  shutdown: () =>
    fetchApi<{ status: string; message: string }>('/shutdown', { method: 'POST' }),
}
